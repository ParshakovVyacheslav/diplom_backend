from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Product(models.Model):

    name = models.CharField(max_length=255, verbose_name='Название')
    extra_info = models.TextField(blank=True, verbose_name='Дополнительная информация')
    net_weight = models.FloatField(default=0.0, verbose_name='Вес нетто (г)', blank=True)
    number_of_servings = models.IntegerField(default=1, verbose_name='Количество порций', blank=True)
    producer = models.CharField(max_length=255, blank=True, verbose_name='Производитель')
    product_category = models.CharField(max_length=100, blank=True, verbose_name='Категория продукта')
    
    calories = models.IntegerField(null=True, blank=True, verbose_name='Калории (ккал)')
    protein = models.FloatField(default=0.0, verbose_name='Белки (г)')
    carbohydrates = models.FloatField(default=0.0, verbose_name='Углеводы (г)')
    fats = models.FloatField(default=0.0, verbose_name='Жиры (г)')

    def __str__(self):
        return f"{self.name})"

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'


class Meal(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='meals',
        verbose_name='Пользователь'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='meals',
        verbose_name='Продукт'
    )
    
    name = models.CharField(max_length=255, verbose_name='Название приема пищи')
    amount = models.IntegerField(default=100, verbose_name='Количество порций')
    
    position = models.IntegerField(default=0, verbose_name='Порядковый номер')
    date = models.DateTimeField(verbose_name='Дата приема пищи', auto_now_add=True)
    
    calories = models.IntegerField(null=True, blank=True, verbose_name='Калории (ккал)')
    protein = models.FloatField(default=0.0, verbose_name='Белки (г)')
    carbohydrates = models.FloatField(default=0.0, verbose_name='Углеводы (г)')
    fats = models.FloatField(default=0.0, verbose_name='Жиры (г)')

    def __str__(self):
        return f"{self.user.username}: {self.name} ({self.date.date()})"

    class Meta:
        verbose_name = 'Прием пищи'
        verbose_name_plural = 'Приемы пищи'
        ordering = ['-date', 'position']