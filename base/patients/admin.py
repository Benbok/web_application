from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('family', 'given', 'show_parents', 'show_children', 'updated_at', 'created_at')
    search_fields = ('family',)
    list_filter = ('birth_date',)

    def show_parents(self, obj):
        return ", ".join([str(parent) for parent in obj.parents.all()])
    show_parents.short_description = "Родители"

    def show_children(self, obj):
        return ", ".join([str(child) for child in obj.children.all()])
    show_children.short_description = "Дети"