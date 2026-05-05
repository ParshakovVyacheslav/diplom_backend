from django.db import transaction
from rest_framework import serializers

from .models import Exercise, TemplateAssignment, WorkoutTemplate
from .validators import (
    SchemaValidationError,
    collect_muscle_groups_for_nodes,
    ids_exist_for_nodes,
    validate_exercise_payload,
    validate_plan_nodes,
)


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


class WorkoutTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutTemplate
        fields = ['id', 'name', 'nodes']
        read_only_fields = ['id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        return data

    def validate_nodes(self, nodes):
        try:
            validate_plan_nodes(nodes)
        except SchemaValidationError as e:
            raise serializers.ValidationError(e.message)
        user = self.context['request'].user
        try:
            ids_exist_for_nodes(user, nodes)
        except SchemaValidationError as e:
            raise serializers.ValidationError(e.message)
        return nodes

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        kind = self.context['template_kind']
        nodes = validated_data['nodes']
        muscle_groups = collect_muscle_groups_for_nodes(user, nodes)
        return WorkoutTemplate.objects.create(
            user=user,
            kind=kind,
            muscle_groups=muscle_groups,
            **validated_data,
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        user = self.context['request'].user
        instance = super().update(instance, validated_data)
        instance.muscle_groups = collect_muscle_groups_for_nodes(user, instance.nodes)
        instance.save(update_fields=['muscle_groups'])
        return instance


class TemplateAssignmentSerializer(serializers.ModelSerializer):
    templateId = serializers.PrimaryKeyRelatedField(source='template', queryset=WorkoutTemplate.objects.all())
    anchorDate = serializers.DateField(source='anchor_date')
    intervalDays = serializers.IntegerField(source='interval_days')
    endDate = serializers.DateField(source='end_date', allow_null=True)
    sortOrder = serializers.IntegerField(source='sort_order')

    class Meta:
        model = TemplateAssignment
        fields = ['id', 'templateId', 'anchorDate', 'intervalDays', 'endDate', 'sortOrder']
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(instance.id)
        data['templateId'] = str(instance.template_id)
        ad = instance.anchor_date
        data['anchorDate'] = ad.isoformat() if ad else None
        ed = instance.end_date
        data['endDate'] = ed.isoformat() if ed else None
        return data

    def validate_template(self, tpl):
        user = self.context['request'].user
        if tpl.user_id != user.id:
            raise serializers.ValidationError('Шаблон не найден')
        return tpl

    def validate(self, data):
        iv = data.get('interval_days')
        if iv is not None and iv < 0:
            raise serializers.ValidationError({'intervalDays': 'Не может быть отрицательным'})
        return data


class DayPlanCompletedSerializer(serializers.Serializer):
    completed = serializers.BooleanField(required=True)
