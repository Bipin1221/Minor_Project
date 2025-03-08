from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.EventsViewSet, basename='events')
# router.register('categories', views.CategoryViewSet, basename='categories')

urlpatterns = [
    path('public-categories/', views.PublicCategoryListView.as_view(), name='category-list'),
    path('public-events/', views.PublicEventsListView.as_view(), name='public-events-list'),
    path('public-events/<int:pk>/', views.PublicEventsDetailView.as_view(), name='public-events-detail'),
    path('<int:pk>/comment/', views.CommentCreateAPIView.as_view(), name='create-comment'),
    path('<int:pk>/rate/', views.RatingCreateAPIView.as_view(), name='create-rating'),
    path('<int:pk>/interest/', views.InterestCreateAPIView.as_view(), name='show-interest'),
    # path('<int:pk>/upload-image/', views.EventImageUploadAPIView.as_view(), name='event-upload-image'),
    path('<int:pk>/purchase-ticket/', views.TicketPurchaseAPIView.as_view(), name='purchase-ticket'),
    path('validate-ticket/<uuid:ticket_id>/', views.TicketValidationAPIView.as_view(), name='validate-ticket'),
    path('my-tickets/', views.UserTicketsAPIView.as_view(), name='user-tickets'),
   
    path('', include(router.urls)),
]


