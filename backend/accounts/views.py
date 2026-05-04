import logging
import requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import ValidateRegistrationCredentialsSerializer

logger = logging.getLogger(__name__)

User = get_user_model()

# Числовые коды ошибок для клиента (зафиксированы в описании операции Swagger)
USERNAME_ALREADY_EXISTS = 1001
PASSWORD_TOO_SHORT = 1002
PASSWORD_TOO_SIMILAR_TO_USER_FIELDS = 1003
PASSWORD_TOO_COMMON = 1004
PASSWORD_ENTIRELY_NUMERIC = 1005
PASSWORD_VALIDATION_FAILED = 1006

DJANGO_PASSWORD_CODE_TO_API = {
    'password_too_short': PASSWORD_TOO_SHORT,
    'password_too_similar': PASSWORD_TOO_SIMILAR_TO_USER_FIELDS,
    'password_too_common': PASSWORD_TOO_COMMON,
    'password_entirely_numeric': PASSWORD_ENTIRELY_NUMERIC,
}


REGISTRATION_CREDENTIAL_ERRORS_SWAGGER_DOC = (
    'Числовой **code** в элементах `errors[]`:\n\n'
    f'- **{USERNAME_ALREADY_EXISTS}** — пользователь с таким никнеймом уже есть\n'
    f'- **{PASSWORD_TOO_SHORT}** — пароль короче минимальной длины '
    '(`MinimumLengthValidator`)\n'
    f'- **{PASSWORD_TOO_SIMILAR_TO_USER_FIELDS}** — пароль слишком похож на указанное '
    'имя пользователя или другие поля (`UserAttributeSimilarityValidator`, '
    'проверка по несохранённому пользователю с переданным `username`)\n'
    f'- **{PASSWORD_TOO_COMMON}** — пароль входит в список распространённых '
    '(`CommonPasswordValidator`)\n'
    f'- **{PASSWORD_ENTIRELY_NUMERIC}** — пароль состоит только из цифр '
    '(`NumericPasswordValidator`)\n'
    f'- **{PASSWORD_VALIDATION_FAILED}** — иное нарушение пароля (кастомные валидаторы '
    'или неизвестный код Django)\n'
)


def _password_error_items(password: str, *, provisional_user: User) -> list[dict]:
    try:
        validate_password(password, user=provisional_user)
    except DjangoValidationError as exc:
        items = []
        for err in exc.error_list:
            django_code = getattr(err, 'code', None)
            api_code = DJANGO_PASSWORD_CODE_TO_API.get(
                django_code, PASSWORD_VALIDATION_FAILED
            )
            detail = next(iter(err))
            items.append({'code': api_code, 'detail': detail})
        return items
    return []


_VALIDATION_SUCCESS_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'valid': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
        ),
    },
)

_VALIDATION_ERROR_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'code': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description=(
                'Числовой код ошибки (расшифровка см. описание этого ответа 400 ниже)'
            ),
        ),
        'detail': openapi.Schema(type=openapi.TYPE_STRING),
    },
    required=['code', 'detail'],
)

_VALIDATION_ERROR_BODY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'errors': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=_VALIDATION_ERROR_ITEM_SCHEMA,
        ),
    },
    required=['errors'],
)


def activate_user(request, uid, token):
    try:
        djoser_url = getattr(
            settings,
            'DJANGO_INTERNAL_ACTIVATION_URL',
            'http://web:8000/auth/users/activation/',
        )

        response = requests.post(
            djoser_url,
            json={'uid': uid, 'token': token},
            timeout=5
        )

        if response.status_code == 204:
            return HttpResponse('''
                <h1>Аккаунт активирован!</h1>
                <p>Теперь вы можете войти в приложение.</p>
            ''')
        else:
            return HttpResponse('''
                <h1>Ошибка активации</h1>
                <p>Ссылка недействительна или устарела.</p>
                <p>Код ошибки: ''' + str(response.status_code) + '''</p>
            ''', status=400)

    except requests.exceptions.RequestException:
        return HttpResponse('''
            <h1>Ошибка соединения</h1>
            <p>Попробуйте позже или свяжитесь с поддержкой.</p>
        ''', status=500)


class ValidateRegistrationCredentialsView(APIView):
    """Проверка username и пароля без создания пользователя."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['auth'],
        operation_id='auth_validate_registration_credentials',
        operation_summary='Проверка логина и пароля перед регистрацией',
        operation_description=(
            'Принимает имя пользователя и пароль. Возвращает 200, если такого '
            'пользователя ещё нет и пароль удовлетворяет всем правилам из '
            '`AUTH_PASSWORD_VALIDATORS`. '
            'Иначе при нарушении правил пароля или уникальности ника — 400 со списком '
            '`errors`; в каждом элементе числовое поле **code** (см. ответ 400) и текст '
            '**detail**. '
            'Если переданы некорректные данные (нет поля, тип и т.д.), возможен ответ 400 '
            'в виде ошибок Django REST Framework по полям (без общего массива `errors`).'
        ),
        request_body=ValidateRegistrationCredentialsSerializer(),
        responses={
            200: openapi.Response(
                'Уникальное имя и допустимый пароль',
                _VALIDATION_SUCCESS_SCHEMA,
            ),
            400: openapi.Response(
                description=(
                    'Неверное тело запроса или нарушение правил доменной проверки. '
                    '\n\n' + REGISTRATION_CREDENTIAL_ERRORS_SWAGGER_DOC
                ),
                schema=_VALIDATION_ERROR_BODY_SCHEMA,
                examples={
                    'application/json': {
                        'errors': [
                            {
                                'code': USERNAME_ALREADY_EXISTS,
                                'detail': 'Уже есть пользователь с таким именем.',
                            },
                        ],
                    },
                },
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = ValidateRegistrationCredentialsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        errors: list[dict] = []
        if User.objects.filter(username=username).exists():
            errors.append(
                {
                    'code': USERNAME_ALREADY_EXISTS,
                    'detail': 'Уже есть пользователь с таким именем.',
                }
            )
        provisional = User(username=username)
        errors.extend(_password_error_items(password, provisional_user=provisional))

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'valid': True}, status=status.HTTP_200_OK)
