from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    surname = models.CharField("Отчество", max_length=150, blank=True)
    email = models.EmailField(_("email address"), unique=True)
    pending_email = models.EmailField(
        _("email pending verification"),
        blank=True,
        default='',
        help_text=_(
            'Новый адрес после запроса смены почты до подтверждения по ссылке из письма.'
        ),
    )
    is_active = models.BooleanField(
        _("active"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]


class ActivityLevel(models.TextChoices):
    LOW = 'low', _('Низкая')
    MEDIUM = 'medium', _('Средняя')
    HIGH = 'high', _('Высокая')


class Sex(models.TextChoices):
    MALE = 'male', _('Мужской')
    FEMALE = 'female', _('Женский')


class NutritionGoal(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='nutrition_goal',
    )
    calories = models.PositiveIntegerField(verbose_name=_('Целевые калории'))
    protein_g = models.FloatField(verbose_name=_('Белки, г'))
    fat_g = models.FloatField(verbose_name=_('Жиры, г'))
    carbs_g = models.FloatField(verbose_name=_('Углеводы, г'))

    class Meta:
        verbose_name = _('цель по КБЖУ')
        verbose_name_plural = _('цели по КБЖУ')


class UserBody(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='body',
    )
    weight_kg = models.FloatField(verbose_name=_('Вес, кг'))
    height_cm = models.PositiveSmallIntegerField(verbose_name=_('Рост, см'))
    age_years = models.PositiveSmallIntegerField(verbose_name=_('Возраст'))
    sex = models.CharField(
        max_length=16,
        choices=Sex.choices,
        verbose_name=_('Пол'),
    )
    activity = models.CharField(
        max_length=16,
        choices=ActivityLevel.choices,
        verbose_name=_('Активность'),
    )

    class Meta:
        verbose_name = _('параметры тела')
        verbose_name_plural = _('параметры тела')


class WeightHistoryEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weight_history',
    )
    date = models.DateField(verbose_name=_('Дата измерения'))
    weight_kg = models.FloatField(verbose_name=_('Вес, кг'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('запись истории веса')
        verbose_name_plural = _('история веса')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'date'),
                name='unique_weight_history_user_date',
            ),
        ]
        ordering = ['-date']