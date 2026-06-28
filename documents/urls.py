from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from documents.auth import TenantTokenView
from documents.views import QueryView

urlpatterns = [
    path("auth/login/", TenantTokenView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("query/", QueryView.as_view(), name="query"),
]