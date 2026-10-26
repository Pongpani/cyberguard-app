from django.urls import path
from scanner import views
urlpatterns = [
    path("api/health/", views.health),
    path("api/scans/url/", views.scan_url),
    path("api/scans/message/", views.scan_message),
    path("api/practice/start/", views.practice_start),
    path("api/practice/submit/", views.practice_submit),
    path("api/statistics/", views.statistics),
    path("", views.index),
]

