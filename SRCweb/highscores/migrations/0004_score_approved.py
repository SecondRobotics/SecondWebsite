# Generated by Django 3.1.5 on 2021-01-15 00:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('highscores', '0003_auto_20210106_0034'),
    ]

    operations = [
        migrations.AddField(
            model_name='score',
            name='approved',
            field=models.BooleanField(default=1),
            preserve_default=False,
        ),
    ]