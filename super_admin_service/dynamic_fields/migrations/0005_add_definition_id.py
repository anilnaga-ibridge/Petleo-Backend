# Generated manually

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_fields', '0004_rename_provider_id_providerdocumentverification_auth_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='providerdocumentverification',
            name='definition_id',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
