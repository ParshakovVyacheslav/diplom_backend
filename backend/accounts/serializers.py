from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer

from accounts import email_change
from accounts.models import NutritionGoal, UserBody, WeightHistoryEntry

User = get_user_model()


class CustomUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'password')
        
    
    def validate_password(self, value):
        validate_password(value)
        return value
        
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            username=validated_data['username']
        )
        return user
    

class CustomUserSerializer(UserSerializer):
    
    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'surname')
        read_only_fields = ('email',)


class ValidateRegistrationCredentialsSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )


class ProfileSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)
    username = serializers.CharField(
        required=False,
        max_length=150,
        validators=[UnicodeUsernameValidator()],
    )
    pending_email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('username', 'email', 'pending_email', 'created_at')
        read_only_fields = ('email', 'created_at')
        extra_kwargs = {'username': {'required': False}}

    def get_pending_email(self, obj):
        return obj.pending_email or None

    def validate_username(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError('Укажите непустое имя пользователя.')
        request = self.context.get('request')
        qs = User.objects.filter(username=name)
        if request and getattr(request.user, 'pk', None):
            qs = qs.exclude(pk=request.user.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Пользователь с таким именем уже существует.'
            )
        return name


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionGoal
        fields = ('calories', 'protein_g', 'fat_g', 'carbs_g')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BodySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBody
        fields = ('weight_kg', 'height_cm', 'age_years', 'sex', 'activity')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class WeightHistoryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightHistoryEntry
        fields = ('id', 'date', 'weight_kg', 'created_at')
        read_only_fields = fields


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField(write_only=True, required=True)

    def validate_new_email(self, value):
        normalized = email_change.normalize_email(value)
        if not normalized:
            raise serializers.ValidationError('Укажите корректный email.')
        return normalized


class EmailChangeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False, required=True)