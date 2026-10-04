from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0002_remove_message_body_message_attachment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="is_admin_support",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="conversation",
            name="human_handoff",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="message",
            name="is_automated",
            field=models.BooleanField(default=False),
        ),
    ]
