from rest_framework import serializers
from .models import Product, Meal
from drf_yasg import openapi

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class MealSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Meal
        fields = ['id', 'product', 'name', 'type', 'amount', 'unit', 'position', 'date',
                  'calories', 'protein', 'carbohydrates', 'fats']
        read_only_fields = ('user', 'calories', 'protein', 'carbohydrates', 'fats')

    @staticmethod
    def _nutrition_from_product(product: Product, amount: int) -> dict:
        factor = amount / 100
        return {
            'calories': (
                None if product.calories is None else int(round(product.calories * factor))
            ),
            'protein': product.protein * factor,
            'carbohydrates': product.carbohydrates * factor,
            'fats': product.fats * factor,
        }

    def validate(self, data):
        if 'product' in data:
            if not Product.objects.filter(id=data['product'].id).exists():
                raise serializers.ValidationError({"product": "Продукт не найден"})
        return data

    def create(self, validated_data):
        product = validated_data['product']
        amount = validated_data.get('amount', 100)
        validated_data.update(self._nutrition_from_product(product, amount))
        return super().create(validated_data)