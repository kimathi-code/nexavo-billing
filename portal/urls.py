from django.urls import path

from . import views


urlpatterns = [
    path(
        "activate/",
        views.portal_activation_view,
        name="portal_activation"
    ),

    path(
        "login/",
        views.portal_login,
        name="portal_login"
    ),

    path(
        "dashboard/",
        views.portal_dashboard,
        name="portal_dashboard"
    ),
    path(
        "activate/resend-code/",
        views.portal_activation_resend_code,
        name="portal_activation_resend_code"
    )
]
