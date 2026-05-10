"""URL конфигурация раздела `/api/profile/`."""

from django.urls import path

from accounts.profile_views import (
    BodyView,
    EmailChangeCancelView,
    EmailChangeConfirmView,
    EmailChangeRequestView,
    GoalView,
    ProfileView,
    WeightHistoryListView,
)

urlpatterns = [
    path('', ProfileView.as_view(), name='api-profile'),
    path('goal/', GoalView.as_view(), name='api-profile-goal'),
    path('body/', BodyView.as_view(), name='api-profile-body'),
    path(
        'email-change/request/',
        EmailChangeRequestView.as_view(),
        name='api-profile-email-change-request',
    ),
    path(
        'email-change/confirm/',
        EmailChangeConfirmView.as_view(),
        name='api-profile-email-change-confirm',
    ),
    path(
        'email-change/',
        EmailChangeCancelView.as_view(),
        name='api-profile-email-change-cancel',
    ),
    path(
        'weight-history/',
        WeightHistoryListView.as_view(),
        name='api-profile-weight-history',
    ),
]
