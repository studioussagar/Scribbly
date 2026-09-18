from django.contrib import admin
from .models import Post, CustomUser, Category, Notification

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date_created')

admin.site.register(Post, PostAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_author', 'approved_for_author']  # Display new approval flag
    list_editable = ['approved_for_author']  # Allow inline editing in list view


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "actor",
        "notification_type",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
    )

    search_fields = (
        "text",
        "recipient__username",
        "actor__username",
    )