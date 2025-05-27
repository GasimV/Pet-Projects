from django.contrib import admin
from .models import UserFeedback, ProductionQuery, FineTuningQuery, UserRequestCount


# Register UserFeedback with a custom admin interface
@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('user_query', 'doc_title', 'relevant_article', 'created_at')
    search_fields = ('user_query__query_text', 'doc_title', 'relevant_article')
    list_filter = ('created_at', 'relevant_article')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50


# Register ProductionQuery with a custom admin interface
@admin.register(ProductionQuery)
class ProductionQueryAdmin(admin.ModelAdmin):
    list_display = ('full_prompt', 'created_at')
    search_fields = ('full_prompt',)
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50


# Register FineTuningQuery with a custom admin interface
@admin.register(FineTuningQuery)
class FineTuningQueryAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'gpt_response', 'created_at')
    search_fields = ('query_text', 'gpt_response')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50


# Register UserRequestCount with a custom admin interface
@admin.register(UserRequestCount)
class UserRequestCountAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'count')
    search_fields = ('user__username', 'user__email')
    list_filter = ('date', 'user')
    ordering = ('-date', 'user')
    date_hierarchy = 'date'
    list_per_page = 50
