from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApproachIsDonePatchView,
    AssignmentByDateView,
    AssignmentIsDonePatchView,
    AssignmentTemplateViewSet,
    ExerciseGlobalListView,
    ExercisePersonalListCreateView,
    WorkoutSetRoundsRemainsPatchView,
)

router = DefaultRouter()
router.register('assignment-templates', AssignmentTemplateViewSet, basename='assignment-template')

urlpatterns = [
    path('', include(router.urls)),
    path('exercises/', ExerciseGlobalListView.as_view({'get': 'list'})),
    path(
        'exercises/personal/',
        ExercisePersonalListCreateView.as_view({'get': 'list', 'post': 'create'}),
    ),
    path('assignments/date/<str:date_iso>/', AssignmentByDateView.as_view()),
    path(
        'assignments/<uuid:assignment_pk>/approaches/<uuid:approach_pk>/',
        ApproachIsDonePatchView.as_view(),
    ),
    path(
        'assignments/<uuid:assignment_pk>/workout-sets/<uuid:workout_set_pk>/',
        WorkoutSetRoundsRemainsPatchView.as_view(),
    ),
    path('assignments/<uuid:pk>/', AssignmentIsDonePatchView.as_view()),
]
