from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("talents", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="TalentMission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("provider_name", models.CharField(max_length=160)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("description", models.TextField()),
                ("mission_type", models.CharField(choices=[("one_off", "Mission ponctuelle"), ("fixed_term", "CDD"), ("permanent", "CDI"), ("internship", "Stage"), ("freelance", "Freelance")], default="one_off", max_length=20)),
                ("starts_at", models.DateField(blank=True, null=True)),
                ("compensation", models.CharField(blank=True, max_length=100)),
                ("skills", models.CharField(blank=True, help_text="Compétences séparées par des virgules", max_length=300)),
                ("is_active", models.BooleanField(default=True)),
                ("is_demo", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
