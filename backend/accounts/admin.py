from django.contrib import admin

from accounts.models import (
    CustomUser,
    NutritionGoal,
    UserBody,
    WeightHistoryEntry,
)

admin.site.register(CustomUser)
admin.site.register(NutritionGoal)
admin.site.register(UserBody)
admin.site.register(WeightHistoryEntry)