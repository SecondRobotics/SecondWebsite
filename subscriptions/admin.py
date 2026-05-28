from django.contrib import admin

from .models import ServerSession, SubscriptionEntitlement, SubscriptionPlan, UsageLedgerEntry, WebhookEvent


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'display_order',
        'name',
        'tier',
        'monthly_price_usd',
        'monthly_server_minutes',
        'max_session_minutes',
        'max_concurrent_servers',
        'entitlement_priority',
        'is_active',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'tier', 'polar_product_id')
    prepopulated_fields = {'tier': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('name', 'tier', 'description', 'benefit_lines', 'is_active'),
        }),
        ('Billing and integrations', {
            'fields': ('monthly_price_usd', 'polar_product_id', 'discord_role_id'),
        }),
        ('Casual server limits', {
            'fields': ('monthly_server_minutes', 'max_session_minutes', 'max_concurrent_servers'),
        }),
        ('Display and entitlement resolution', {
            'fields': ('display_order', 'entitlement_priority'),
        }),
    )


@admin.register(SubscriptionEntitlement)
class SubscriptionEntitlementAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'provider', 'status', 'current_period_start', 'current_period_end', 'cancel_at_period_end')
    list_filter = ('provider', 'status', 'plan')
    search_fields = ('user__username', 'user__display_name', 'provider_subscription_id', 'provider_customer_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ServerSession)
class ServerSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'game', 'game_code', 'orchestrator_session_id', 'host', 'port', 'allocated_minutes', 'ready_at', 'stopped_at')
    list_filter = ('status', 'game')
    search_fields = ('id', 'user__username', 'user__display_name', 'server_identifier', 'orchestrator_session_id', 'host')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(UsageLedgerEntry)
class UsageLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'entitlement', 'minutes', 'reason', 'billing_period_start', 'billing_period_end', 'created_at')
    list_filter = ('reason',)
    search_fields = ('user__username', 'user__display_name')


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('provider', 'event_type', 'event_id', 'status', 'received_at', 'processed_at')
    list_filter = ('provider', 'status', 'event_type')
    search_fields = ('event_id', 'event_type')
    readonly_fields = ('received_at', 'processed_at')
