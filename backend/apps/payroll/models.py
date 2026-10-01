from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Payslip(models.Model):
    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="payslips")
    period_month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    period_year = models.PositiveSmallIntegerField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_year", "-period_month"]
        unique_together = [("employee", "period_month", "period_year")]

    def __str__(self):
        return f"{self.employee} — {self.period_month:02d}/{self.period_year}"

    @property
    def net_pay(self):
        return self.base_salary + self.bonuses + self.allowances - self.deductions
