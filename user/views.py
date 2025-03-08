"""
Views for the user API.
"""
from rest_framework import generics, authentication, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.settings import api_settings
from django.core.mail import send_mail
from django.conf import settings
from user.serializers import UserSerializer, AuthTokenSerializer,PasswordChangeSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'message': 'User created successfully',
            'data': response.data
        }, status=status.HTTP_201_CREATED)

class CreateTokenView(APIView):
    """Create a new auth token for user."""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, 
                                         context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        
        # Create or get existing token
        token, created = Token.objects.get_or_create(user=user)
        
        # Send email with token (uncomment to enable)
        # send_mail(
        #     subject="Your Authentication Token",
        #     message=f"Your authentication token is: {token.key}",
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[user.email],
        #     fail_silently=False,
        # )

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        }, status=status.HTTP_200_OK)

class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=partial
        )
        serializer.is_valid(raise_exception=True)

        # Prevent role update for non-admins
        if 'role' in serializer.validated_data and not request.user.is_staff:
            serializer.validated_data.pop('role')
        if 'email' in serializer.validated_data:
            serializer.validated_dataa.pop('email')
        
        self.perform_update(serializer)
        return Response(serializer.data)

class ManageUserByAdminView(generics.RetrieveUpdateAPIView):
    """Manage user details by admin."""
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            'message': 'User updated successfully',
            'data': response.data
        }, status=status.HTTP_200_OK)
    

class ChangePasswordView(generics.GenericAPIView):
    serializer_class =PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post (self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)


        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {"current_password": ["Current password is incorrect"]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Password updated successfully"})