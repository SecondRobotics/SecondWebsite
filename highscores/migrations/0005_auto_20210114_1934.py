# Generated by Django 3.1.5 on 2021-01-15 00:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('highscores', '0004_score_approved'),
    ]

    operations = [
        migrations.AlterField(
            model_name='score',
            name='approved',
            field=models.BooleanField(default=False),
        ),
    ]