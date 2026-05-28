import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import orchestrator
from .models import ServerSession, SubscriptionPlan
from .services import (
    SubscriptionError,
    WebhookVerificationError,
    create_polar_checkout_url,
    entitlement_payload,
    launch_casual_server,
    process_polar_webhook,
    request_stop_server_session,
    verify_standard_webhook_signature,
)


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@login_required(login_url='/login')
def subscription_home(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'monthly_price_usd', 'name')
    entitlement = entitlement_payload(request.user)
    sessions = ServerSession.objects.filter(user=request.user).order_by('-started_at')[:10]
    casual_games = []
    games_error = ''
    if entitlement.get('active') and orchestrator.is_configured():
        try:
            casual_games = orchestrator.get_casual_games()
        except orchestrator.OrchestratorError as exc:
            games_error = str(exc)
    return render(request, 'subscriptions/home.html', {
        'plans': plans,
        'entitlement': entitlement,
        'sessions': sessions,
        'casual_games': casual_games,
        'games_error': games_error,
        'orchestrator_configured': orchestrator.is_configured(),
        'customer_portal_url': getattr(settings, 'POLAR_CUSTOMER_PORTAL_URL', ''),
    })


@login_required(login_url='/login')
def checkout(request, tier):
    try:
        plan = SubscriptionPlan.objects.get(tier=tier, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        messages.error(request, 'That subscription plan is not available.')
        return redirect('/subscriptions/')

    try:
        return redirect(create_polar_checkout_url(request.user, plan, customer_ip_address=_get_client_ip(request)))
    except SubscriptionError as exc:
        messages.error(request, str(exc))
        return redirect('/subscriptions/')


@login_required(login_url='/login')
@require_POST
def launch_server_session(request):
    try:
        session = launch_casual_server(
            request.user,
            requested_minutes=request.POST.get('requested_minutes'),
            game=request.POST.get('game_name') or request.POST.get('game_code', ''),
            game_code=request.POST.get('game_code', ''),
            comment=request.POST.get('comment', ''),
            password=request.POST.get('password', ''),
            launch_source='website',
            launch_context={'source': 'website'},
        )
    except SubscriptionError as exc:
        messages.error(request, str(exc))
        return redirect('/subscriptions/')

    messages.success(request, f'Casual server launch requested. Session {session.id} is starting.')
    return redirect('/subscriptions/')


@login_required(login_url='/login')
@require_POST
def stop_server_session_view(request, session_id):
    try:
        session = ServerSession.objects.get(id=session_id, user=request.user)
    except ServerSession.DoesNotExist:
        messages.error(request, 'Server session does not exist.')
        return redirect('/subscriptions/')

    try:
        request_stop_server_session(session, reason='website_stop')
    except SubscriptionError as exc:
        messages.error(request, str(exc))
        return redirect('/subscriptions/')

    messages.success(request, 'Server stop requested.')
    return redirect('/subscriptions/')


@csrf_exempt
@require_POST
def polar_webhook(request):
    webhook_id = request.META.get('HTTP_WEBHOOK_ID', '')
    webhook_timestamp = request.META.get('HTTP_WEBHOOK_TIMESTAMP', '')
    webhook_signature = request.META.get('HTTP_WEBHOOK_SIGNATURE', '')

    try:
        verify_standard_webhook_signature(
            getattr(settings, 'POLAR_WEBHOOK_SECRET', ''),
            request.body,
            webhook_id,
            webhook_timestamp,
            webhook_signature,
        )
    except WebhookVerificationError as exc:
        return HttpResponseBadRequest(str(exc))

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON payload.')

    event = process_polar_webhook(payload, event_id=webhook_id)
    return JsonResponse({'success': True, 'status': event.status})
