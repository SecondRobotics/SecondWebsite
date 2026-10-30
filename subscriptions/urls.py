from django.urls import path

from . import views

urlpatterns = [
    path('', views.subscription_home, name='subscriptions home'),
    path('checkout/<str:tier>/', views.checkout, name='subscriptions checkout'),
    path('server-sessions/launch/', views.launch_server_session, name='subscriptions launch server'),
    path('server-sessions/<uuid:session_id>/stop/', views.stop_server_session_view, name='subscriptions stop server'),
    path('polar/webhook/', views.polar_webhook, name='polar webhook'),
]
