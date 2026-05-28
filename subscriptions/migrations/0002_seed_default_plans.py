from django.db import migrations


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')
    defaults = [
        {
            'tier': 'supporter',
            'name': 'Supporter',
            'description': 'Premium Discord role and light casual server hosting.',
            'benefit_lines': 'Premium Discord role\nLaunch from Discord bot or website',
            'monthly_price_usd': 5,
            'monthly_server_minutes': 360,
            'max_session_minutes': 120,
            'max_concurrent_servers': 1,
            'display_order': 10,
            'entitlement_priority': 10,
        },
        {
            'tier': 'host',
            'name': 'Host',
            'description': 'More casual server hours and longer hosting sessions.',
            'benefit_lines': 'Higher premium Discord role\nSaved casual presets / faster relaunch flow',
            'monthly_price_usd': 12,
            'monthly_server_minutes': 1500,
            'max_session_minutes': 240,
            'max_concurrent_servers': 1,
            'display_order': 20,
            'entitlement_priority': 20,
        },
    ]
    for plan in defaults:
        SubscriptionPlan.objects.update_or_create(
            tier=plan['tier'],
            defaults=plan,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_plans, migrations.RunPython.noop),
    ]
