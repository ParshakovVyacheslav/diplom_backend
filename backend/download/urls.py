from django.urls import path

from download.views import DownloadApkView, DownloadPageView

urlpatterns = [
    path('', DownloadPageView.as_view(), name='download-page'),
    path('apk/', DownloadApkView.as_view(), name='download-apk'),
]
