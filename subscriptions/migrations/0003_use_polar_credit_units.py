from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0002_seed_default_plans'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subscriptionplan',
            old_name='monthly_server_minutes',
            new_name='monthly_credits',
        ),
        migrations.AlterField(
            model_name='subscriptionplan',
            name='monthly_credits',
            field=models.PositiveIntegerField(help_text='Credits granted by the plan each billing period. Casual servers currently consume 1 credit per runtime minute.'),
        ),
        migrations.RenameField(
            model_name='usageledgerentry',
            old_name='minutes',
            new_name='credits',
        ),
    ]
