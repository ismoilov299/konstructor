from django.contrib import admin
from .models import SystemChannel

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
    search_fields = ['admin_channel', 'bot_token']
    list_display = ['admin_channel', 'price', 'min_amount', 'bot_token']
    list_editable = ['price', 'min_amount']
    ordering = ['-id']
    list_filter = ['bot_token']


@admin.register(Channels)
class ChannelsAdmin(admin.ModelAdmin):
    search_fields = ['channel_id']
    list_display = ['channel_id']
    ordering = ['-id']


@admin.register(SystemChannel)
class SystemChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_id', 'title', 'is_active', 'added_by_user_id', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'channel_id', 'channel_url']
    list_editable = ['is_active']
    ordering = ['-created_at']
    readonly_fields = ['channel_id', 'added_by_user_id', 'created_at']