from django.contrib import admin

from .models import Subscription, User


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'username',
        'first_name',
        'last_name',
        'password',
    )
    list_filter = (
        'email',
        'username',
    )
    empty_value_display = '-пусто-'


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'subscriber',
        'author',
    )
    empty_value_display = '-пусто-'


admin.site.register(User, UserProfileAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
