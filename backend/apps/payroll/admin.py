from django.contrib import admin

from .models import Payslip


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ["employee", "period_month", "period_year", "base_salary", "net_pay"]
    list_filter = ["period_year", "period_month"]
