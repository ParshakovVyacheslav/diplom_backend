from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignmentByDateView,
    AssignmentTemplateViewSet,
    ExerciseGlobalListView,
    ExercisePersonalListCreateView,
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
]
