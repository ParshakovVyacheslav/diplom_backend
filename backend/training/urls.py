from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignmentViewSet,
    DayPlanCompletedPatchView,
    DayPlanView,
    ExerciseGlobalListView,
    ExercisePersonalListCreateView,
    PlanViewSet,
    SetViewSet,
)

router = DefaultRouter()
router.register(r'plans', PlanViewSet, basename='training-plan')
router.register(r'sets', SetViewSet, basename='training-set')
router.register(r'assignments', AssignmentViewSet, basename='training-assignment')

urlpatterns = [
    path('', include(router.urls)),
    path('exercises/', ExerciseGlobalListView.as_view({'get': 'list'})),
    path(
        'exercises/personal/',
        ExercisePersonalListCreateView.as_view({'get': 'list', 'post': 'create'}),
    ),
    path('day-plan/', DayPlanView.as_view()),
    path('day-plan/<str:date_iso>/completed/', DayPlanCompletedPatchView.as_view()),
]
