from rest_framework import serializers

from .models import Payslip


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    net_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id", "employee", "employee_name", "period_month", "period_year",
            "base_salary", "bonuses", "allowances", "deductions", "net_pay", "generated_at",
        ]
        read_only_fields = ["id", "generated_at"]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"
