from django.contrib import admin
from .models import ApplicationAnalysis,WriterApplication

@admin.register(ApplicationAnalysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("application",)

@admin.register(WriterApplication)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("submitted_title",)