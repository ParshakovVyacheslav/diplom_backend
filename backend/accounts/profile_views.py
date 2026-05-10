from datetime import date, datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.core import signing
from django.http import HttpResponse
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import email_change as ec
from accounts.models import NutritionGoal, UserBody, WeightHistoryEntry
from accounts.serializers import (
    BodySerializer,
    EmailChangeConfirmSerializer,
    EmailChangeRequestSerializer,
    GoalSerializer,
    ProfileSerializer,
    WeightHistoryEntrySerializer,
)

_PROFILE_FIELDS_READ = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'username': openapi.Schema(type=openapi.TYPE_STRING),
        'email': openapi.Schema(type=openapi.TYPE_STRING),
        'pending_email': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_EMAIL,
            description=(
                'Не подтверждённый адрес после POST /email-change/request; '
                'null если заявки нет.'
            ),
        ),
        'created_at': openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATETIME,
        ),
    },
)

_PROFILE_BODY_WRITE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'username': openapi.Schema(type=openapi.TYPE_STRING),
    },
)

_EMAIL_CHANGE_REQUEST = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'new_email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
    },
    required=['new_email'],
)

_EMAIL_CHANGE_CONFIRM_BODY = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'token': openapi.Schema(
            type=openapi.TYPE_STRING,
            description=(
                'Тот же token, что в ссылке из письма (подходит для мобильного клиента без открытия браузера)'
            ),
        ),
    },
    required=['token'],
)

_GOAL_FIELDS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'calories': openapi.Schema(type=openapi.TYPE_INTEGER),
        'protein_g': openapi.Schema(type=openapi.TYPE_NUMBER),
        'fat_g': openapi.Schema(type=openapi.TYPE_NUMBER),
        'carbs_g': openapi.Schema(type=openapi.TYPE_NUMBER),
    },
    required=['calories', 'protein_g', 'fat_g', 'carbs_g'],
)

_BODY_FIELDS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'weight_kg': openapi.Schema(type=openapi.TYPE_NUMBER),
        'height_cm': openapi.Schema(type=openapi.TYPE_INTEGER),
        'age_years': openapi.Schema(type=openapi.TYPE_INTEGER),
        'sex': openapi.Schema(type=openapi.TYPE_STRING, enum=['male', 'female']),
        'activity': openapi.Schema(
            type=openapi.TYPE_STRING, enum=['low', 'medium', 'high']
        ),
    },
    required=['weight_kg', 'height_cm', 'age_years', 'sex', 'activity'],
)

_WEIGHT_ITEM = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        'weight_kg': openapi.Schema(type=openapi.TYPE_NUMBER),
        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
    },
)

_WEIGHT_ITEMS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'items': openapi.Schema(type=openapi.TYPE_ARRAY, items=_WEIGHT_ITEM),
    },
)

def _parse_iso_date(raw: str) -> date | None:
    raw = raw.strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if parsed.tzinfo:
            parsed = parsed.astimezone(dt_timezone.utc)
        return parsed.date()
    except ValueError:
        return None


def _record_weight_history_if_changed(user, old_weight_kg: float, new_weight_kg: float) -> None:
    if old_weight_kg == new_weight_kg:
        return
    today = timezone.now().date()
    WeightHistoryEntry.objects.update_or_create(
        user=user,
        date=today,
        defaults={'weight_kg': new_weight_kg},
    )


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Текущий профиль',
        operation_description=(
            'Имя пользователя (username) совпадает с логином в Djoser. '
            'Сменить email здесь нельзя — используйте /email-change/request/.'
        ),
        responses={200: openapi.Response('', _PROFILE_FIELDS_READ), 401: 'Не авторизован'},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Обновление профиля (PUT)',
        request_body=_PROFILE_BODY_WRITE,
        responses={200: openapi.Response('', _PROFILE_FIELDS_READ), 400: '', 401: ''},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Частичное обновление профиля',
        request_body=_PROFILE_BODY_WRITE,
        responses={200: openapi.Response('', _PROFILE_FIELDS_READ), 400: '', 401: ''},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class GoalView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Текущая цель по КБЖУ',
        responses={200: openapi.Response('', _GOAL_FIELDS), 401: '', 404: 'Цель не задана'},
    )
    def get(self, request):
        goal = NutritionGoal.objects.filter(user=request.user).first()
        if goal is None:
            return Response(
                {'detail': 'Цель не задана.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(GoalSerializer(goal).data)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Создать цель по КБЖУ',
        request_body=_GOAL_FIELDS,
        responses={
            201: openapi.Response('', _GOAL_FIELDS),
            400: '',
            401: '',
            409: 'Цель уже существует — используйте PUT/PATCH',
        },
    )
    def post(self, request):
        if NutritionGoal.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Цель уже существует; измените её через PATCH или PUT.'},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = GoalSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Полная замена цели',
        request_body=_GOAL_FIELDS,
        responses={200: '', 400: '', 401: '', 404: ''},
    )
    def put(self, request):
        goal = NutritionGoal.objects.filter(user=request.user).first()
        if goal is None:
            return Response(
                {'detail': 'Цель не задана. Сначала выполните POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GoalSerializer(goal, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Частичное изменение цели',
        request_body=_GOAL_FIELDS,
        responses={200: '', 400: '', 401: '', 404: ''},
    )
    def patch(self, request):
        goal = NutritionGoal.objects.filter(user=request.user).first()
        if goal is None:
            return Response(
                {'detail': 'Цель не задана. Сначала выполните POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GoalSerializer(goal, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Удалить цель',
        responses={204: 'Удалено', 401: '', 404: ''},
    )
    def delete(self, request):
        deleted = NutritionGoal.objects.filter(user=request.user).delete()[0]
        if not deleted:
            return Response(
                {'detail': 'Цель не задана.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BodyView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Параметры тела',
        responses={200: openapi.Response('', _BODY_FIELDS), 401: '', 404: ''},
    )
    def get(self, request):
        body = UserBody.objects.filter(user=request.user).first()
        if body is None:
            return Response(
                {'detail': 'Параметры тела не заданы.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(BodySerializer(body).data)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Создать параметры тела',
        request_body=_BODY_FIELDS,
        responses={
            201: openapi.Response('', _BODY_FIELDS),
            400: '',
            401: '',
            409: 'Запись уже есть — используйте PATCH/PUT',
        },
    )
    def post(self, request):
        if UserBody.objects.filter(user=request.user).exists():
            return Response(
                {
                    'detail': 'Параметры тела уже заданы; измените через PATCH или PUT.',
                },
                status=status.HTTP_409_CONFLICT,
            )
        serializer = BodySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Полная замена параметров тела',
        request_body=_BODY_FIELDS,
        responses={200: '', 400: '', 401: '', 404: ''},
    )
    def put(self, request):
        body = UserBody.objects.filter(user=request.user).first()
        if body is None:
            return Response(
                {'detail': 'Параметры не заданы. Сначала выполните POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BodySerializer(body, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        old_w = body.weight_kg
        instance = serializer.save()
        _record_weight_history_if_changed(request.user, old_w, instance.weight_kg)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Частичное обновление параметров тела',
        request_body=_BODY_FIELDS,
        responses={200: '', 400: '', 401: '', 404: ''},
    )
    def patch(self, request):
        body = UserBody.objects.filter(user=request.user).first()
        if body is None:
            return Response(
                {'detail': 'Параметры не заданы. Сначала выполните POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BodySerializer(body, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        old_w = body.weight_kg
        instance = serializer.save()
        _record_weight_history_if_changed(request.user, old_w, instance.weight_kg)
        return Response(serializer.data)


class WeightHistoryListView(generics.ListAPIView):
    serializer_class = WeightHistoryEntrySerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='История веса',
        manual_parameters=[
            openapi.Parameter(
                name='from',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='ISO 8601 date (YYYY-MM-DD), начало периода включительно',
            ),
            openapi.Parameter(
                name='to',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='ISO 8601 date, конец периода включительно',
            ),
            openapi.Parameter(
                name='limit',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='Лимит записей (по умолчанию 365, максимум 500)',
            ),
        ],
        responses={200: openapi.Response('', _WEIGHT_ITEMS_RESPONSE), 401: '', 400: ''},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return WeightHistoryEntry.objects.filter(user=self.request.user).order_by('date')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        qp = request.query_params

        dt_from_raw = qp.get('from')
        if dt_from_raw:
            parsed = _parse_iso_date(dt_from_raw)
            if parsed is None:
                raise ValidationError({'from': ['Неверный формат даты.']})
            qs = qs.filter(date__gte=parsed)

        dt_to_raw = qp.get('to')
        if dt_to_raw:
            parsed = _parse_iso_date(dt_to_raw)
            if parsed is None:
                raise ValidationError({'to': ['Неверный формат даты.']})
            qs = qs.filter(date__lte=parsed)

        limit_raw = qp.get('limit', '365')
        try:
            limit = max(1, min(int(limit_raw), 500))
        except (TypeError, ValueError):
            raise ValidationError({'limit': ['Ожидалось целое число.']})

        serializer = self.get_serializer(qs[:limit], many=True)
        return Response({'items': serializer.data})


User = get_user_model()


def _html_email_change_result(*, ok: bool, title: str, text: str) -> HttpResponse:
    from django.utils.html import escape

    color = '#0a0' if ok else '#a00'
    body = (
        f'<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"/>'
        f'<title>{escape(title)}</title></head><body>'
        f'<h1 style="color:{color}">{escape(title)}</h1>'
        f'<p>{escape(text)}</p></body></html>'
    )
    return HttpResponse(body, content_type='text/html; charset=utf-8')


class EmailChangeRequestView(APIView):
    """Запрос смены почты: письмо на новый адрес с ссылкой подтверждения."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Запросить смену email',
        operation_description=(
            'Основной email в учётке меняется только после перехода по ссылке из письма, '
            'отправленного на **новый** адрес. Текущий PATCH /api/profile/ не меняет email.'
        ),
        request_body=_EMAIL_CHANGE_REQUEST,
        responses={200: '', 400: '', 401: ''},
    )
    def post(self, request):
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        normalized = serializer.validated_data['new_email']
        current = ec.normalize_email(request.user.email)
        if normalized == current:
            raise ValidationError(
                {'new_email': ['Этот адрес уже является текущим email учётной записи.']}
            )
        if User.objects.exclude(pk=request.user.pk).filter(
            email__iexact=normalized
        ).exists():
            raise ValidationError({'new_email': ['Этот email уже занят.']})

        user = request.user
        user.pending_email = normalized
        user.save(update_fields=['pending_email'])

        raw = ec.issue_email_change_token(user.pk, normalized)
        confirm_url = ec.resolve_confirm_link(request, raw)
        ec.send_email_change_confirmation(
            to_email=normalized,
            confirm_url=confirm_url,
        )
        return Response(
            {
                'detail': (
                    'Письмо с подтверждением отправлено на новый адрес. '
                    'Перейдите по ссылке из письма, чтобы завершить смену.'
                )
            },
            status=status.HTTP_200_OK,
        )


class EmailChangeConfirmView(APIView):
    """Подтверждение смены почты (GET из браузера по ссылке или POST с token из клиента)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Подтвердить смену email (ссылка из письма, GET)',
        manual_parameters=[
            openapi.Parameter(
                'token',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='Значение query-параметра token из письма',
            ),
        ],
        responses={200: 'HTML-страница с результатом'},
    )
    def get(self, request):
        raw = (request.query_params.get('token') or '').strip()
        if not raw:
            return _html_email_change_result(
                ok=False,
                title='Ошибка',
                text='Отсутствует параметр token.',
            )
        try:
            finalized = ec.apply_pending_email_change_from_token(raw)
        except signing.SignatureExpired:
            return _html_email_change_result(
                ok=False,
                title='Ссылка устарела',
                text='Запросите смену почты снова.',
            )
        except signing.BadSignature:
            return _html_email_change_result(
                ok=False,
                title='Недействительная ссылка',
                text='Проверьте, что вы скопировали ссылку целиком.',
            )
        except ValueError as exc:
            code = str(exc)
            if code == 'TOKEN_MISMATCH':
                msg = (
                    'Ссылка больше не действительна (например, запрошена новая смена '
                    'или заявка отменена). Повторите запрос смены почты.'
                )
            elif code == 'EMAIL_TAKEN':
                msg = (
                    'Этот адрес уже используется другой учётной записью. '
                    'Выберите другой email.'
                )
            else:
                msg = 'Не удалось подтвердить смену почты.'
            return _html_email_change_result(
                ok=False,
                title='Не удалось подтвердить',
                text=msg,
            )
        return _html_email_change_result(
            ok=True,
            title='Почта обновлена',
            text=f'Новый адрес сохранён: {finalized}',
        )

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Подтвердить смену email (POST, для приложения)',
        request_body=_EMAIL_CHANGE_CONFIRM_BODY,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            400: '',
        },
    )
    def post(self, request):
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw = serializer.validated_data['token'].strip()
        try:
            finalized = ec.apply_pending_email_change_from_token(raw)
        except signing.SignatureExpired:
            raise ValidationError(
                {'token': ['Ссылка устарела. Запросите смену почты ещё раз.']}
            )
        except signing.BadSignature:
            raise ValidationError(
                {'token': ['Неверный или повреждённый token.']}
            )
        except ValueError as exc:
            code = str(exc)
            if code == 'TOKEN_MISMATCH':
                raise ValidationError(
                    {
                        'token': [
                            'Этот token больше не действителен (новая заявка '
                            'или отмена). Запросите смену снова.',
                        ]
                    }
                )
            if code == 'EMAIL_TAKEN':
                raise ValidationError(
                    {
                        'token': [
                            'Этот адрес уже занят другой учётной записью.',
                        ]
                    }
                )
            raise ValidationError({'token': ['Не удалось подтвердить смену почты.']})
        return Response(
            {'detail': 'Адрес электронной почты обновлён.', 'email': finalized},
            status=status.HTTP_200_OK,
        )


class EmailChangeCancelView(APIView):
    """Отмена неподтверждённой смены (`pending_email` сбрасывается)."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Профиль'],
        operation_summary='Отменить запрошенную смену email',
        responses={204: 'pending_email очищен', 401: ''},
    )
    def delete(self, request):
        User.objects.filter(pk=request.user.pk).update(pending_email='')
        return Response(status=status.HTTP_204_NO_CONTENT)
