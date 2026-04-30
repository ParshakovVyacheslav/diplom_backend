from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer

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