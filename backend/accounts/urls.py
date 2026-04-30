from django.urls import path

from accounts.views import ValidateRegistrationCredentialsView, activate_user

urlpatterns = [
    path('activate/<str:uid>/<str:token>/', activate_user, name='activate-user'),
    path(
        'validate-registration-credentials/',
        ValidateRegistrationCredentialsView.as_view(),
        name='validate-registration-credentials',
    ),
]