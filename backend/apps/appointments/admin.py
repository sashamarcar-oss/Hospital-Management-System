from django.contrib import admin

from apps.appointments.models import Appointment, Queue

admin.site.register(Appointment)
admin.site.register(Queue)
