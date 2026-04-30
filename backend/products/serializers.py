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
    
    def validate(self, data):
        if 'product' in data:
            if not Product.objects.filter(id=data['product'].id).exists():
                raise serializers.ValidationError({"product": "Продукт не найден"})
        return data