import qrcode
import logging
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)

def generate_qr_code(ticket):
    """Generate QR code with ticket details."""
    qr_data = (
        f"Ticket ID: {ticket.id}\n"
        f"Event: {ticket.event.title}\n"
        f"User: {ticket.user.email}\n"
        f"Type: {ticket.ticket_type}"
    )
    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return ContentFile(buffer.getvalue(), f"qr_{ticket.id}.png")

def generate_ticket_pdf(tickets):
    """Generate a well-structured ticket PDF with proper alignment and spacing."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter
    margin = 72  # 1 inch margins
    
    for ticket in tickets:
        # Configure layout parameters
        content_width = page_width - 2*margin
        y_position = page_height - margin  # Start from top margin
        
        # Draw Header Section
        p.setFont("Helvetica-Bold", 20)
        p.drawString(margin, y_position, ticket.event.user.name)
        p.setFont("Helvetica", 12)
        y_position -= 25
        p.drawString(margin, y_position, "Present this entire page at the Venue")
        y_position -= 40  # Space after header

        # Two-column layout setup
        col_width = content_width / 2 - 20
        details_x = margin
        qr_x = margin + col_width + 40

        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(details_x, y_position, ticket.event.title)
        y_position -= 30

        # Event Details (Left Column) - FIXED DATE FORMATTING
        p.setFont("Helvetica", 12)
        details = [
            ("Date:", ticket.event.event_dates.strftime('%Y-%m-%d')),  # Format date
            ("Time:", ticket.event.time_start.strftime('%I:%M %p')),
            ("Venue:", ticket.event.venue_name),
            ("Ticket Type:", ticket.ticket_type),
            ("Purchased By: ", ticket.user.email),
            ("Purchase Date: ", ticket.purchased_at.strftime('%Y-%m-%d %H:%M')),  # Format datetime
            ("Ticket ID:", str(ticket.id)),  # Ensure ID is string
        ]

        detail_y = y_position
        for label, value in details:
            p.setFont("Helvetica-Bold", 12)
            p.drawString(details_x, detail_y, label)
            p.setFont("Helvetica", 12)
            p.drawString(details_x + 120, detail_y, str(value))  # Explicit string conversion
            detail_y -= 25  # Line spacing

        if ticket.qr_code:
            try:
                qr_size = 150
                qr_image = Image.open(ticket.qr_code.path)
                qr_image = qr_image.resize((qr_size, qr_size))
                
                p.drawInlineImage(qr_image, qr_x, y_position - 50, 
                                width=qr_size, height=qr_size)
            except Exception as e:
                p.setFont("Helvetica", 10)
                p.drawString(qr_x, y_position, f"QR Code Error: {str(e)}")

        # Visual Separator
        separator_y = detail_y - 30
        p.line(margin, separator_y, page_width - margin, separator_y)

        # Footer Notice
        p.setFont("Helvetica-Oblique", 10)
        footer_text = "Valid ID required for entry • No refunds or exchanges • Ticket valid only for purchased event"
        p.drawCentredString(page_width/2, 40, footer_text)

        p.showPage()

    p.save()
    buffer.seek(0)
    return buffer.getvalue()

def send_ticket_email(tickets):
    """Send email with attached PDF of tickets."""
    try:
        if not tickets:
            logger.warning("No tickets provided for email")
            return

        # Validate tickets belong to the same user/event
        user = tickets[0].user
        event = tickets[0].event
        for ticket in tickets[1:]:
            if ticket.user != user or ticket.event != event:
                raise ValueError("All tickets must belong to the same user and event")

        # Build email
        email = EmailMessage(
            subject=f"Your {len(tickets)} Ticket(s) for {event.title}",
            body=(
                f"Hello {user.name},\n\n"
                f"Attached are your {len(tickets)} ticket(s) for:\n"
                f"Event: {event.title}\n"
                f"Date: {event.event_dates}\n"
                f"Venue: {event.venue_name}\n\n"
                "Thank you for your purchase!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        
        # Attach PDF
        pdf = generate_ticket_pdf(tickets)
        email.attach(
            f"tickets_{event.id}.pdf",
            pdf,
            "application/pdf"
        )
        
        email.send(fail_silently=False)
        logger.info(f"Sent {len(tickets)} tickets to {user.email}")

    except Exception as e:
        logger.error(f"Failed to send tickets: {str(e)}", exc_info=True)
        raise Exception("Failed to send tickets")