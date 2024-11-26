from django.contrib import admin

from .models import Bot, ClientBotUser, User, UserTG, AdminInfo, Channels


# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'uid']
    list_filter = ['created_at']
    list_display = ['uid', 'username']
    ordering = ['-id']


@admin.register(UserTG)
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'uid']
    list_filter = ['created_at']
    list_display = ['uid', 'username']
    ordering = ['-id']


@admin.register(ClientBotUser)
class ClientBotUserAdmin(admin.ModelAdmin):
    search_fields = ['uid']
    list_display = ['uid', 'balance']
    ordering = ['-id']


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    search_fields = ['username']
    list_display = ['id', 'username', 'owner']
    ordering = ['-id']


@admin.register(AdminInfo)
class AdminInfoAdmin(admin.ModelAdmin):
    search_fields = ['admin_channel']
    list_display = ['admin_channel']
    ordering = ['-id']


@admin.register(Channels)
class ChannelsAdmin(admin.ModelAdmin):
    search_fields = ['channel_id']
    list_display = ['channel_id']
    ordering = ['-id']