from django.urls import path

from .views import ExerciseGlobalListView, ExercisePersonalListCreateView

urlpatterns = [
    path('exercises/', ExerciseGlobalListView.as_view({'get': 'list'})),
    path(
        'exercises/personal/',
        ExercisePersonalListCreateView.as_view({'get': 'list', 'post': 'create'}),
    ),
]
