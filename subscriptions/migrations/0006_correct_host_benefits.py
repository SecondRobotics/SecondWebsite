from django.db import migrations


def correct_unimplemented_benefit(apps, schema_editor):
    plans = apps.get_model('subscriptions', 'SubscriptionPlan')
    for plan in plans.objects.all():
        lines = plan.benefit_lines.splitlines()
        if 'Saved casual presets / faster relaunch flow' not in lines:
            continue
        lines.remove('Saved casual presets / faster relaunch flow')
        if 'Launch from Discord bot or website' not in lines:
            lines.append('Launch from Discord bot or website')
        plan.benefit_lines = '\n'.join(lines)
        plan.save(update_fields=['benefit_lines'])


class Migration(migrations.Migration):
    dependencies = [('subscriptions', '0005_serversession_billing_period_end_and_more')]
    operations = [migrations.RunPython(correct_unimplemented_benefit, migrations.RunPython.noop)]
