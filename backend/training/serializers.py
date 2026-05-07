from rest_framework import serializers

from .models import Exercise
from .validators import SchemaValidationError, validate_exercise_payload


class ExerciseSerializer(serializers.ModelSerializer):
    mainMuscles = serializers.ListField(source='main_muscles')
    muscleGroup = serializers.CharField(source='muscle_group')
    description = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = Exercise
        fields = ['id', 'name', 'description', 'mainMuscles', 'muscleGroup', 'approaches']
        read_only_fields = ['id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        return data


class ExerciseWriteSerializer(serializers.ModelSerializer):
    """Создание личного упражнения (camelCase из спецификации)."""

    id = serializers.UUIDField(read_only=True)
    mainMuscles = serializers.ListField(source='main_muscles')
    muscleGroup = serializers.CharField(source='muscle_group')
    description = serializers.CharField(allow_null=True, required=False, allow_blank=True)

    class Meta:
        model = Exercise
        fields = ['id', 'name', 'description', 'mainMuscles', 'muscleGroup', 'approaches']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        return data

    def validate(self, data):
        merged = {
            'name': data.get('name'),
            'description': data.get('description'),
            'mainMuscles': data.get('main_muscles'),
            'muscleGroup': data.get('muscle_group'),
            'approaches': data.get('approaches'),
        }
        try:
            validate_exercise_payload(
                {
                    'name': merged['name'],
                    'description': merged['description'],
                    'mainMuscles': merged['mainMuscles'],
                    'muscleGroup': merged['muscleGroup'],
                    'approaches': merged['approaches'],
                },
                require_id=False,
            )
        except SchemaValidationError as e:
            raise serializers.ValidationError(e.message)
        return data
