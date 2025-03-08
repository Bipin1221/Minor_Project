from rest_framework import viewsets, mixins, status, generics,filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny,BasePermission
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Count
from .utils import send_ticket_email
from  core.models import Events,Ticket

from core.models import Events, Category, Interest, Rating,Ticket
from .serializers import (
    EventCreateUpdateSerializer,
    EventListSerializer,
    EventDetailSerializer,
    PublicEventsSerializer,
    PublicEventsDetailSerializer,
    CommentSerializer,
    RatingSerializer,
    InterestSerializer,
  
    CategorySerializer,
    TicketSerializer,
    KhaltiInitiateSerializer
)
from django.urls import reverse
from rest_framework.authtoken.models import Token
import logging
from rest_framework import serializers
logger = logging.getLogger(__name__)
from django.utils import timezone
from rest_framework.views import APIView
from io import BytesIO
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from rest_framework.request import Request
import requests

from .utils import send_ticket_email

from django.shortcuts import get_object_or_404

from .serializers import TicketSerializer


class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'organizer'



# from rest_framework.parsers import MultiPartParser, FormParser

class EventsViewSet(viewsets.ModelViewSet):
    # parser_classes = (MultiPartParser, FormParser)
    queryset = Events.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsOrganizer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
   
    search_fields = ['title','category__name', 'venue_location'] 

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EventCreateUpdateSerializer
        if self.action == 'list':
            return EventListSerializer
        return EventDetailSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)\
                   .prefetch_related('category')\
                   .order_by('-created_at')
# class EventImageUploadAPIView(generics.GenericAPIView):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [TokenAuthentication]
#     serializer_class = EventImageSerializer
#     def post(self, request, pk=None):
#         event = get_object_or_404(Events, pk=pk)  # Get the event instance

       
#         if self.request.user.role != 'organizer':
#             raise PermissionDenied("Only organizer can upload images")

#         # Check if the image is in the request files
#         if 'image' not in request.FILES:
#             raise ValidationError("No image provided")

#         # Save the image to the event
#         event.image = request.FILES['image']
#         event.save()

#         # Return the image URL in the response
#         return Response({'image_url': event.image.url}, status=status.HTTP_200_OK)

# class CategoryViewSet(mixins.ListModelMixin,
#                      viewsets.GenericViewSet):
#     serializer_class = CategorySerializer
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated, IsOrganizer]
    
    # def get_queryset(self):
    #     return Category.objects.filter(user=self.request.user)

class PublicEventsListView(generics.ListAPIView):
    serializer_class = PublicEventsSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
   
    search_fields = ['title','category__name', 'venue_location'] 
    def get_queryset(self):
        return Events.objects.annotate(interest_count = Count('interests')).order_by('-interest_count','-created_at')
    

class PublicCategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    queryset = Category.objects.all()

      
class PublicEventsDetailView(generics.RetrieveAPIView):
    serializer_class = PublicEventsDetailSerializer
    permission_classes = [AllowAny]
    queryset = Events.objects.all()

class CommentCreateAPIView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        event = get_object_or_404(Events, pk=self.kwargs['pk'])
        if self.request.user.role != 'attendee':
            raise PermissionDenied("Only attendees can comment")
        serializer.save(user=self.request.user, event=event)

class RatingCreateAPIView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        event = get_object_or_404(Events, pk=self.kwargs['pk'])
        if self.request.user.role != 'attendee':
            raise PermissionDenied("Only attendees can rate events")
        if Rating.objects.filter(user=self.request.user, event=event).exists():
            raise ValidationError("You've already rated this event")
        serializer.save(user=self.request.user, event=event)

class InterestCreateAPIView(generics.CreateAPIView):
    serializer_class = InterestSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        event = get_object_or_404(Events, pk=self.kwargs['pk'])
        if self.request.user.role != 'attendee':
            raise PermissionDenied("Only attendees can show interest")
        if Interest.objects.filter(user=self.request.user, event=event).exists():
            raise ValidationError("You've already shown interest")
        serializer.save(user=self.request.user, event=event)
 
class TicketPurchaseAPIView(generics.CreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        event = get_object_or_404(Events, pk=self.kwargs['pk'])
        user = self.request.user
        quantity = serializer.validated_data.get('quantity', 1)
        # Role check
        if user.role != 'attendee':
            raise PermissionDenied(detail="Only attendees can purchase tickets.")
        
        # Purchase limits
        tickets = []
        for _ in range(quantity):
            ticket = Ticket.objects.create(
                user=user,
                event=event,
                ticket_type=serializer.validated_data['ticket_type'],
                quantity=1  # Each ticket represents 1 entry
            )
            tickets.append(ticket)

        send_ticket_email(tickets)
        
        logger.info(f"Ticket {ticket.id} created for {user.email}")

class TicketValidationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id)
        organizer = request.user
        
        # Role check
        if organizer.role != 'organizer':
            raise PermissionDenied(detail="Only organizers can validate tickets.")
        
        # Ownership check
        if ticket.event.user != organizer:
            raise PermissionDenied(detail="You don't have permission to validate this ticket.")
        
        # Validation check
        
            
        if ticket.validated_count >= 1:
            return Response(
                {"error": "Ticket already validated."},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate ticket
        ticket.validated_count = 1
        ticket.save()
        
        return Response(
            {
                "status": "validated",
                "ticket_id": str(ticket.id),
                "event": ticket.event.title,
                "attendee": ticket.user.email,
                "ticeket_used": ticket.delete()
            },
            status=status.HTTP_200_OK
            
        
        )
       
        

class UserTicketsAPIView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'attendee':
            raise PermissionDenied(detail="Only attendees can view their tickets.")
        return Ticket.objects.filter(user=user).select_related('event')
    





class KhaltiInitiatePaymentAPIView(APIView):
    """
    Initiates a Khalti payment for a given product.
    """
    permission_classes = [IsAuthenticated] # or permission_classes = [IsAuthenticated]
    serializer_class = KhaltiInitiateSerializer

    def post(self, request):
        serializer = KhaltiInitiateSerializer(data=request.data)
        if serializer.is_valid():
            event_id = serializer.validated_data['event_id']
            amount = serializer.validated_data['amount']
            try:
                event=get_object_or_404(Events, id=event_id)
                #ticket = get_object_or_404(Ticket, event_id=event_id)  # Use Events model instead of Product
                amount = int(amount * 100)  # Access the ticket_price and Convert NPR to paisa. Ensure Events has ticket_price

                payload = {
                    "return_url": request.build_absolute_uri(reverse("khalti_payment_callback")),
                    "website_url": "https://yourwebsite.com/",
                    "amount": amount,
                    "purchase_order_id": f"order_{event.id}",
                    "purchase_order_name": event.title,
                    "merchant_username": "Event Ticketing System",
                    "merchant_extra": "merchant_extra"  
                }

                headers = {
                    "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
                    "Content-Type": "application/json"
                }

                # Debugging: Print request data before sending it
                logger.info(f"Initiating Khalti Payment with: {payload}")
                logger.info(f"Using Secret Key: {settings.KHALTI_SECRET_KEY}")

                response = requests.post(settings.KHALTI_INITIATE_URL, json=payload, headers=headers)

                # Debugging: Print response
                logger.info(f"Khalti Response Status: {response.status_code}")
                logger.info(f"Khalti Response Data: {response.text}")

                if response.status_code == 200:
                    data = response.json()
                    return Response({"payment_url": data["payment_url"]}, status=status.HTTP_200_OK)  # Return the payment URL
                else:
                    return Response({"error": "Payment initiation failed", "details": response.text}, status=response.status_code)

            except Events.DoesNotExist:
                return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class KhaltiVerifyAPIView(APIView):
#     """
#     Verifies a Khalti payment.
#     """
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = KhaltiVerifySerializer(data=request.data)
#         if serializer.is_valid():
#             token = serializer.validated_data['token']
#             amount = serializer.validated_data['amount']

#             headers = {
#                 "Authorization": f"Key {settings.KHALTI_SECRET_KEY}"
#             }

#             data = {
#                 "token": token,
#                 "amount": amount
#             }

#             response = requests.post(settings.KHALTI_VERIFY_URL, data=data, headers=headers)

#             if response.status_code == 200:
#                 return Response({"status": "success", "message": "Payment verified!"}, status=status.HTTP_200_OK)
#             else:
#                 return Response({"status": "failure", "message": "Verification failed", "details": response.json()}, status=response.status_code)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KhaltiPaymentCallbackView(APIView):
    def get(self, request):
        logger = logging.getLogger(__name__)
        pidx = request.GET.get("pidx")
        amount = request.GET.get("amount")

        if not pidx or not amount:
            return Response({"error": "Invalid payment request. Missing pidx or amount."}, status=status.HTTP_400_BAD_REQUEST)

        headers = {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"}
        verify_url = "https://a.khalti.com/api/v2/epayment/lookup/"
        verify_payload = {"pidx": pidx}

        logger.info(f"Sending verification request to Khalti with: {verify_payload}")
        verify_response = requests.post(verify_url, json=verify_payload, headers=headers)

        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            logger.info(f"Khalti Verification Response: {verify_data}")

            if verify_data.get("status") == "Completed":
                # Call the ticket API after successful payment verification
                id = 2
                ticket_url = f"http://127.0.0.1:8000/api/events/{id}/comment/"  # Replace with actual ticket API URL
                ticket_payload = {
                            "text": f"hey this is auto comment on id {id}"
                                }
                ticket_headers = {"Authorization": "Token 4f53178b4c14a615e40faa15f4dd8d4247281edf"}  # Adjust as needed
                ticket_response = requests.post(url=ticket_url, json=ticket_payload, headers=ticket_headers)
                print(ticket_response)

                if ticket_response.status_code == 201:
                    return Response({"message": "Payment Successful! Ticket generated.", "amt": amount}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Payment successful, but ticket generation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"error": "Payment verification failed. Please contact support."}, status=status.HTTP_400_BAD_REQUEST)