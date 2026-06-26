from django.urls import path
from . import views

urlpatterns=[
    path('', views.client_list, name='client_list'),
    path('add/', views.create_client, name='create_client'),
    path('success', views.client_success, name='client_success'),
    path('edit/<int:id>/', views.edit_client, name='edit_client'),
    path('delete/<int:id>/', views.delete_client, name='delete_client'),
    path('subscribe/', views.create_subscription, name='create_subscription'),
    path('active/', views.active_clients, name='active_clients'),
    path('expired/', views.expired_clients, name='expired_clients'),
    path('no-subscription/', views.no_subscription_clients, name='no_subscription_clients'),
    path('payments/add/', views.create_payment, name='create_payment'),
    path('billing-dashboard/', views.billing_dashboard, name='billing_dashboard'),
    path(
        'mpesa/callback/',
        views.mpesa_callback,
        name='mpesa_callback'
    ),

    path(
        "mpesa/stk-push/",
        views.initiate_stk_push_view,
        name="initiate_stk_push"
    ), 

    path(
        "mpesa/stk-callback/",
        views.stk_push_callback,
        name="stk_push_callback"
    ),
]
