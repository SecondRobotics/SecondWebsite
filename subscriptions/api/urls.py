from django.urls import path

from . import views

app_name = 'api-subscriptions'

urlpatterns = [
    path('me/entitlement/', views.my_entitlement, name='my entitlement'),
    path('users/<str:discord_user_id>/entitlement/', views.user_entitlement, name='user entitlement'),
    path('casual-games/', views.casual_games, name='casual games'),
    path('server-sessions/start/', views.start_session, name='start session'),
    path('server-sessions/<uuid:session_id>/stop/', views.stop_session, name='stop session'),
    path('server-sessions/<uuid:session_id>/heartbeat/', views.heartbeat_session, name='heartbeat session'),
    path('server-sessions/<uuid:session_id>/orchestrator-event/', views.orchestrator_event, name='orchestrator event'),
]
