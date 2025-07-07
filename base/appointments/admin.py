from django.contrib import admin
from .models import AppointmentEvent

@admin.register(AppointmentEvent)
class AppointmentEventAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'start', 'end', 'status')
    list_filter = ('status', 'doctor')


# project/urls.py (главный urls.py твоего проекта)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/appointments/', include('appointments.urls')),
]