from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class TenantTokenSerializer(TokenObtainPairSerializer):
    """Adds tenant_id into the JWT when a user logs in."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Bake the tenant_id into the token itself
        token["tenant_id"] = user.userprofile.tenant_id
        token["tenant_name"] = user.userprofile.tenant.name
        return token


class TenantTokenView(TokenObtainPairView):
    """Login endpoint that returns a tenant-aware token."""
    serializer_class = TenantTokenSerializer