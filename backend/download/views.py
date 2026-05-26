from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views import View


def get_apk_path() -> Path | None:
    configured = (getattr(settings, 'MOBILE_APK_PATH', '') or '').strip()
    if not configured:
        return None
    path = Path(configured)
    if path.is_file():
        return path
    return None


class DownloadPageView(View):
    def get(self, request):
        apk_path = get_apk_path()
        return render(
            request,
            'download/app.html',
            {
                'site_name': settings.SITE_NAME,
                'apk_available': apk_path is not None,
                'apk_filename': apk_path.name if apk_path else '',
            },
        )


class DownloadApkView(View):
    def get(self, request):
        apk_path = get_apk_path()
        if not apk_path:
            raise Http404('Файл приложения не найден')

        return FileResponse(
            apk_path.open('rb'),
            as_attachment=True,
            filename=apk_path.name,
            content_type='application/vnd.android.package-archive',
        )
