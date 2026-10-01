from django.db import migrations, models


def ensure_plan_marketplace_type(apps, schema_editor):
    Plan = apps.get_model("marketplace", "SubscriptionPlan")
    columns = {column.name for column in schema_editor.connection.introspection.get_table_description(schema_editor.connection.cursor(), Plan._meta.db_table)}
    if "marketplace_type" not in columns:
        field = models.CharField(max_length=30, choices=[("sale", "Marketplace vente"), ("interior_design", "Décoration & design intérieur"), ("actors", "Marketplace des acteurs"), ("venues", "Salles de réception"), ("talent_missions", "Missions pour talents")], null=True, blank=True, help_text="Vide = formule commune. Choisissez Missions pour talents pour son tarif dédié.")
        field.set_attributes_from_name("marketplace_type")
        field.model = Plan
        schema_editor.add_field(Plan, field)


def seed_talent_plan(apps, schema_editor):
    Plan = apps.get_model("marketplace", "SubscriptionPlan")
    Plan.objects.get_or_create(
        code="talent_1_month",
        defaults={
            "label": "30 jours — Missions talent", "months": 1, "duration_days": 30,
            "price": 1000, "discount_percent": 0, "order": 0,
            "marketplace_type": "talent_missions",
        },
    )


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0020_remove_professionalprofile_is_verified_and_more")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ensure_plan_marketplace_type, migrations.RunPython.noop)],
            state_operations=[migrations.AddField(
                model_name="subscriptionplan", name="marketplace_type",
                field=models.CharField(blank=True, choices=[("sale", "Marketplace vente"), ("interior_design", "Décoration & design intérieur"), ("actors", "Marketplace des acteurs"), ("venues", "Salles de réception"), ("talent_missions", "Missions pour talents")], help_text="Vide = formule commune. Choisissez Missions pour talents pour son tarif dédié.", max_length=30, null=True),
            )],
        ),
        migrations.AlterField(
            model_name="commissionsettings", name="marketplace_type",
            field=models.CharField(choices=[("sale", "Marketplace vente"), ("interior_design", "Décoration & design intérieur"), ("actors", "Marketplace des acteurs"), ("venues", "Salles de réception"), ("talent_missions", "Missions pour talents")], max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="marketplacefeature", name="marketplace_type",
            field=models.CharField(choices=[("sale", "Marketplace vente"), ("interior_design", "Décoration & design intérieur"), ("actors", "Marketplace des acteurs"), ("venues", "Salles de réception"), ("talent_missions", "Missions pour talents")], max_length=20),
        ),
        migrations.AlterField(
            model_name="marketplacesubscription", name="marketplace_type",
            field=models.CharField(choices=[("sale", "Marketplace vente"), ("interior_design", "Décoration & design intérieur"), ("actors", "Marketplace des acteurs"), ("venues", "Salles de réception"), ("talent_missions", "Missions pour talents")], max_length=20),
        ),
        migrations.AlterField(
            model_name="marketplacelisting", name="marketplace_type",
            field=models.CharField(choices=[("sale", "Marketplace vente"), ("interior_design", "Décoration & design intérieur"), ("actors", "Marketplace des acteurs"), ("venues", "Salles de réception"), ("talent_missions", "Missions pour talents")], max_length=20),
        ),
        migrations.RunPython(seed_talent_plan, migrations.RunPython.noop),
    ]
