from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Player, Game, GameAnalysis, Profile, Transaction

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('username', 'date_joined')
    search_fields = ('username',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'credits', 'bullet_rating', 'blitz_rating', 'rapid_rating', 'classical_rating', 'total_games', 'win_rate')
    search_fields = ('user__username',)
    list_filter = ('bullet_rating', 'blitz_rating', 'rapid_rating', 'classical_rating')
    readonly_fields = ('win_rate',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'preferences' in form.base_fields:
            form.base_fields['preferences'].initial = {
                "theme": "light",
                "email_notifications": True,
                "analysis_depth": 20
            }
        if 'rating_history' in form.base_fields:
            form.base_fields['rating_history'].initial = {
                "bullet": [],
                "blitz": [],
                "rapid": [],
                "classical": []
            }
        return form

    def save_model(self, request, obj, form, change):
        # Ensure preferences is a valid JSON object
        if not obj.preferences:
            obj.preferences = {}
        
        # Ensure rating_history is a valid JSON object
        if not obj.rating_history:
            obj.rating_history = {
                "bullet": [],
                "blitz": [],
                "rapid": [],
                "classical": []
            }
        
        super().save_model(request, obj, form, change)

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'white', 'black', 'result', 'platform', 'date_played', 'opening_name')
    list_filter = ('platform', 'result', 'date_played')
    search_fields = ('white', 'black', 'user__username', 'opening_name')
    ordering = ('-date_played',)
    raw_id_fields = ('user',)

@admin.register(GameAnalysis)
class GameAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('game__white', 'game__black', 'game__user__username')
    ordering = ('-created_at',)
    raw_id_fields = ('game',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'transaction_type', 'credits', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__username', 'stripe_payment_id')
    ordering = ('-created_at',)
    raw_id_fields = ('user',)