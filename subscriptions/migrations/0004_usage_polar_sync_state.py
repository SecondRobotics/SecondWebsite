from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0003_use_polar_credit_units'),
    ]

    operations = [
        migrations.AddField(
            model_name='usageledgerentry',
            name='polar_error',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='usageledgerentry',
            name='polar_last_attempt_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usageledgerentry',
            name='polar_status',
            field=models.CharField(
                choices=[
                    ('not_required', 'Not Required'),
                    ('pending', 'Pending'),
                    ('sent', 'Sent'),
                    ('failed', 'Failed'),
                ],
                default='not_required',
                max_length=24,
            ),
        ),
        migrations.AddIndex(
            model_name='usageledgerentry',
            index=models.Index(fields=['polar_status'], name='subscriptio_polar_s_9533a3_idx'),
        ),
    ]
