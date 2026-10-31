from django.urls import re_path

from .views import flask_application

urlpatterns = [
    re_path(r"^(?:.*)$", flask_application),
]
