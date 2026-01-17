import os
import django
from django.contrib.auth import get_user_model


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

User = get_user_model()

username = os.getenv('DJANGO_SUPERUSER_USERNAME')
email = os.getenv('DJANGO_SUPERUSER_EMAIL')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if not all([username, email, password]):
    print('Ошибка: переменные окружения не заданы')
    exit(1)

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        is_active=True
    )
    print(f'Суперпользователь {username} создан')
else:
    print(f'Пользователь {username} уже существует')