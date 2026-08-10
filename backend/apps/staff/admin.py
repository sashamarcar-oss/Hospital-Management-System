from django.contrib import admin

from apps.staff.models import Attendance, LeaveRequest, Shift, Staff

admin.site.register(Staff)
admin.site.register(Shift)
admin.site.register(Attendance)
admin.site.register(LeaveRequest)
