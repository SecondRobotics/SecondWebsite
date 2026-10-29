from django.db import migrations


def correct_unimplemented_benefit(apps, schema_editor):
    plans = apps.get_model('subscriptions', 'SubscriptionPlan')
    plans.objects.filter(
        tier='host', benefit_lines='Higher premium Discord role\nSaved casual presets / faster relaunch flow',
    ).update(benefit_lines='Higher premium Discord role\nLaunch from Discord bot or website')


class Migration(migrations.Migration):
    dependencies = [('subscriptions', '0005_serversession_billing_period_end_and_more')]
    operations = [migrations.RunPython(correct_unimplemented_benefit, migrations.RunPython.noop)]
