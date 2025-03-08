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
    TicketSerializer
)
import logging
logger = logging.getLogger(__name__)
from django.utils import timezone
from rest_framework.views import APIView
from io import BytesIO
from django_filters.rest_framework import DjangoFilterBackend


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