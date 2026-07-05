from django.urls import path

from . import views


urlpatterns = [
    path(
        "activate/",
        views.portal_activation_view,
        name="portal_activation"
    ),

]
