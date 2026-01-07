from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, MealViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'meals', MealViewSet)

urlpatterns = [
    path('', include(router.urls)),
]