from rest_framework import serializers
from core.models import Events, Category, Interest, Comment, Rating, Ticket
from rest_framework.exceptions import ValidationError

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']
        read_only_fields = ['id']


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    category = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True
    )
    event_dates = serializers.DateField(format="%Y-%m-%d")
    time_start = serializers.TimeField(format='%H:%M:%S')
    user = serializers.StringRelatedField()
    image = serializers.ImageField(required = False)

    class Meta:
        model = Events
        fields = ['id', 'title', 'event_dates', 'time_start',
                  'venue_name', 'venue_location', 'venue_capacity', 
                   'description', 'category','vip_price','common_price','user','image'
                  ]
        read_only_fields = ['id']

    def create(self, validated_data):
        category_names = validated_data.pop('category', [])
        event = Events.objects.create(
            user=self.context['request'].user,
            **validated_data
        )
        self._handle_categories(category_names, event)
        return event

    def update(self, instance, validated_data):
        category_names = validated_data.pop('category', None)
        if category_names is not None:
            instance.category.clear()
            self._handle_categories(category_names, instance)
        return super().update(instance, validated_data)

    def _handle_categories(self, category_names, event):
        for name in category_names:
            normalized_name = name.strip().lower()
            cat, _ = Category.objects.get_or_create(name=normalized_name)
            event.category.add(cat)

class EventListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(many=True)
    event_dates = serializers.DateField(format="%Y-%m-%d")
    time_start = serializers.TimeField(format='%H:%M:%S')
    interest_count = serializers.SerializerMethodField()
    image = serializers.ImageField(required = False)
    class Meta:
        model = Events
        fields = ['id', 'title', 'event_dates', 'time_start', 'category', 'interest_count','image']

    def get_interest_count(self, obj):
        return obj.interests.count()
class EventDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(many=True)
    comments = serializers.SerializerMethodField()
    interested_count = serializers.SerializerMethodField()
    ratings = serializers.SerializerMethodField()
    event_dates = serializers.DateField(format="%Y-%m-%d")
    time_start = serializers.TimeField(format='%H:%M:%S')
    user = serializers.StringRelatedField(read_only=True)
    vip_price = serializers.DecimalField(max_digits=10,decimal_places=2,required = False)
    common_price = serializers.DecimalField(max_digits=10,decimal_places=2,required = False)
    class Meta:
        model = Events
        fields = [
            'id', 'title', 'event_dates', 'time_start',
             'venue_name', 'venue_location', 'venue_capacity', 
            'description', 'image', 'category',
              'comments', 'ratings', 'user','vip_price','common_price','interested_count'
        ]

    def get_comments(self, obj):
        return CommentSerializer(obj.comments.all(), many=True).data

    def get_ratings(self, obj):
        return RatingSerializer(obj.ratings.all(), many=True).data
    def get_interested_count(self, obj):
        return obj.interests.count()

class PublicEventsSerializer(EventListSerializer):
    
    
    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields
        

class PublicEventsDetailSerializer(EventDetailSerializer):
   
    
    class Meta(EventDetailSerializer.Meta):
        fields = EventDetailSerializer.Meta.fields 

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class RatingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Rating
        fields = ['id', 'user', 'value', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'user', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

# class EventImageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EventImage
#         fields = ['id', 'image', 'uploaded_at']
#         read_only_fields = ['id', 'uploaded_at']


class TicketSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    user_email = serializers.StringRelatedField(source='event.user.email', read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'event_title', 'user_email', 
            'ticket_type', 'qr_code', 'quantity',
        ]
        read_only_fields = ['id', 'qr_code']
        write_only_fields = ['quantity']