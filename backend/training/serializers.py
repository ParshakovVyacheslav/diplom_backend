from django.db.models import Prefetch, Q
from rest_framework import serializers

from .models import Approach, Assignment, AssignmentTemplate, Exercise, WorkoutSet
from .services import normalized_days_of_week
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


# —— AssignmentTemplate / Assignment ——


class ApproachNestedReadSerializer(serializers.ModelSerializer):
    exerciseId = serializers.SerializerMethodField()
    exerciseName = serializers.SerializerMethodField()
    setsCount = serializers.IntegerField(source='sets_count', read_only=True)
    weightKg = serializers.FloatField(source='weight_kg', allow_null=True, read_only=True)
    isDone = serializers.BooleanField(source='is_done', read_only=True)

    class Meta:
        model = Approach
        fields = ('id', 'exerciseId', 'exerciseName', 'weightKg', 'reps', 'setsCount', 'order', 'isDone')

    def get_exerciseId(self, obj):
        return str(obj.exercise_id)

    def get_exerciseName(self, obj):
        return obj.exercise.name

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        return data


class WorkoutSetReadSerializer(serializers.ModelSerializer):
    approaches = ApproachNestedReadSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutSet
        fields = ('id', 'name', 'order', 'approaches')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        return data


class AssignmentTemplateReadSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    endDate = serializers.DateField(source='end_date', allow_null=True)
    daysOfWeek = serializers.ListField(source='days_of_week', child=serializers.IntegerField(min_value=0, max_value=6))
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    sets = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentTemplate
        fields = ('id', 'name', 'endDate', 'daysOfWeek', 'isActive', 'sets')

    def get_sets(self, obj):
        return WorkoutSetReadSerializer(obj.workout_sets.all(), many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        return data


class AssignmentReadSerializer(serializers.ModelSerializer):
    assignmentId = serializers.UUIDField(source='id', read_only=True)
    date = serializers.DateField()
    template = AssignmentTemplateReadSerializer(read_only=True)
    isDone = serializers.BooleanField(source='is_done', read_only=True)

    class Meta:
        model = Assignment
        fields = ('assignmentId', 'date', 'template', 'isDone')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['assignmentId'] = str(instance.id)
        return data


def _validate_weekdays_list(value):
    try:
        normalized_days_of_week(value)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc)) from exc
    seen = []
    uniq = []
    for x in value:
        i = int(x)
        if i not in seen:
            seen.append(i)
            uniq.append(i)
    return uniq


class ApproachNestedWriteSerializer(serializers.Serializer):
    exerciseId = serializers.UUIDField()
    weightKg = serializers.FloatField(required=False, allow_null=True)
    reps = serializers.IntegerField(min_value=1)
    setsCount = serializers.IntegerField(min_value=1)
    order = serializers.IntegerField(required=False, min_value=0, default=0)
    isDone = serializers.BooleanField(required=False, default=False)

    def validate_exerciseId(self, value):
        user = self.context['request'].user
        exists = Exercise.objects.filter(id=value).filter(Q(user__isnull=True) | Q(user=user)).exists()
        if not exists:
            raise serializers.ValidationError('Упражнение не найдено или недоступно')
        return value


class WorkoutSetNestedWriteSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)
    order = serializers.IntegerField(required=False, min_value=0, default=0)
    approaches = ApproachNestedWriteSerializer(many=True)

    def validate_approaches(self, value):
        if not value:
            raise serializers.ValidationError('В каждом сете должен быть хотя бы один подход')
        return value


class AssignmentTemplatePutSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    endDate = serializers.DateField(required=False, allow_null=True)
    daysOfWeek = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6))
    scheduleStartDate = serializers.DateField(required=False)
    isActive = serializers.BooleanField(required=False)
    sets = WorkoutSetNestedWriteSerializer(many=True)

    def validate_daysOfWeek(self, value):
        return _validate_weekdays_list(value)

    def validate_sets(self, value):
        if not value:
            raise serializers.ValidationError('Шаблон должен содержать хотя бы один сет')
        return value


class AssignmentTemplatePatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    endDate = serializers.DateField(required=False, allow_null=True)
    daysOfWeek = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), required=False, allow_empty=False
    )
    scheduleStartDate = serializers.DateField(required=False)
    isActive = serializers.BooleanField(required=False)
    sets = WorkoutSetNestedWriteSerializer(many=True, required=False)

    def validate_daysOfWeek(self, value):
        return _validate_weekdays_list(value)


class StandaloneAssignmentPutSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    endDate = serializers.DateField(required=False, allow_null=True)
    daysOfWeek = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), required=False, allow_empty=False
    )
    sets = WorkoutSetNestedWriteSerializer(many=True)

    def validate_daysOfWeek(self, value):
        return _validate_weekdays_list(value)

    def validate_sets(self, value):
        if not value:
            raise serializers.ValidationError('Нужна непустая структура сетов')
        return value


def prefetch_template_nested(qs):
    appr = Approach.objects.select_related('exercise').order_by('order', 'id')
    return qs.prefetch_related(
        Prefetch(
            'workout_sets',
            queryset=WorkoutSet.objects.order_by('order', 'id').prefetch_related(
                Prefetch('approaches', queryset=appr),
            ),
        ),
    )


class AssignmentIsDonePatchSerializer(serializers.Serializer):
    isDone = serializers.BooleanField()


class ApproachIsDonePatchSerializer(serializers.Serializer):
    isDone = serializers.BooleanField()


def prefetch_assignments_nested(qs):
    appr = Approach.objects.select_related('exercise').order_by('order', 'id')
    return qs.select_related('template').prefetch_related(
        Prefetch(
            'template__workout_sets',
            queryset=WorkoutSet.objects.order_by('order', 'id').prefetch_related(
                Prefetch('approaches', queryset=appr),
            ),
        ),
    )
