from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from documents.auth import TenantTokenView
from documents.views import HealthView, IngestView, QueryView, RegisterView, UsageView

urlpatterns = [
    # Auth
    path("auth/login/", TenantTokenView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/register/", RegisterView.as_view(), name="register"),

    # Core RAG
    path("query/", QueryView.as_view(), name="query"),
    path("ingest/", IngestView.as_view(), name="ingest"),

    # Ops
    path("health/", HealthView.as_view(), name="health"),
    path("usage/", UsageView.as_view(), name="usage"),
]
