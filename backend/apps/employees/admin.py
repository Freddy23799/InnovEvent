from django.contrib import admin

from .models import Employee, JobApplication


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["last_name", "first_name", "position", "hire_date", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["last_name", "first_name"]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["full_name", "desired_position", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["full_name", "email", "desired_position"]
