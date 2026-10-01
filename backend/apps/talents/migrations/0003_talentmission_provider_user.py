import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("talents", "0002_talentmission"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [migrations.AddField(
        model_name="talentmission", name="provider_user",
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="talent_missions", to=settings.AUTH_USER_MODEL),
    )]
