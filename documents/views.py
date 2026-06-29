import os
import tempfile

from django.contrib.auth.models import User
from django.db import connection
from django.db.models import F
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from documents.models import DocumentChunk, Tenant, UserProfile
from documents.services.ingestion import ingest_csv
from documents.services.prompts import VALID_TEMPLATES
from documents.services.rag import rag_query


class QueryView(APIView):
    """
    POST a question; get a grounded answer from YOUR tenant's data only.
    Tenant_id is read from the JWT — never from the request body.
    """

    def post(self, request):
        tenant = request.user.userprofile.tenant

        # --- quota check (1b) ---
        if tenant.requests_used >= tenant.api_quota:
            return Response(
                {
                    "error": "Monthly quota exceeded.",
                    "quota": tenant.api_quota,
                    "used": tenant.requests_used,
                },
                status=429,
            )

        query = request.data.get("query", "").strip()
        if not query:
            return Response({"error": "query is required"}, status=400)

        template = request.data.get("template", "qa")
        if template not in VALID_TEMPLATES:
            return Response(
                {"error": f"Unknown template '{template}'. Valid: {VALID_TEMPLATES}"},
                status=400,
            )

        # Atomically increment before generation so concurrent requests can't
        # both slip under the quota cap.
        Tenant.objects.filter(pk=tenant.pk).update(requests_used=F("requests_used") + 1)

        result = rag_query(query, tenant_id=tenant.id, template=template)
        return Response(result)


class IngestView(APIView):
    """
    Upload a CSV to ingest into the authenticated user's tenant.
    Tenant comes from the JWT — users can only load data into their own tenant.
    """
    parser_classes = [MultiPartParser]

    def post(self, request):
        tenant = request.user.userprofile.tenant

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file uploaded (field name must be 'file')"}, status=400)

        if not uploaded.name.endswith(".csv"):
            return Response({"error": "Only .csv files are accepted"}, status=400)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
            for chunk in uploaded.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = ingest_csv(tmp_path, tenant.name, source_name=uploaded.name)
        finally:
            os.remove(tmp_path)

        return Response({
            "status": "ingested",
            "chunks_created": result["created"],
            "rows_skipped": result["skipped"],
            "tenant": tenant.name,
        })


class HealthView(APIView):
    """GET /api/health/ — public liveness check."""
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        chunk_count = DocumentChunk.objects.count() if db_ok else None
        return Response({
            "status": "ok" if db_ok else "degraded",
            "db": "ok" if db_ok else "error",
            "chunk_count": chunk_count,
        })


class UsageView(APIView):
    """GET /api/usage/ — authenticated; returns caller's quota stats."""

    def get(self, request):
        tenant = request.user.userprofile.tenant
        # Re-fetch for fresh numbers (could have changed since JWT was issued)
        tenant.refresh_from_db()
        return Response({
            "tenant": tenant.name,
            "api_quota": tenant.api_quota,
            "requests_used": tenant.requests_used,
            "remaining": max(0, tenant.api_quota - tenant.requests_used),
        })


class RegisterView(APIView):
    """
    POST /api/auth/register/ — create a user and assign them to a tenant.

    Tenant assignment is derived server-side from the email domain:
      • If an existing tenant has domain == email_domain → use it.
      • Otherwise create/get a tenant named after the domain.
    The caller never picks a tenant by id or name directly.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not username or not email or not password:
            return Response({"error": "username, email, and password are required"}, status=400)

        if "@" not in email:
            return Response({"error": "Invalid email address"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered"}, status=400)

        domain = email.split("@")[1]

        # Domain-based tenant lookup: exact match on the domain field first,
        # then fall back to creating a tenant named after the domain.
        tenant = Tenant.objects.filter(domain=domain).first()
        if tenant is None:
            tenant, _ = Tenant.objects.get_or_create(
                name=domain,
                defaults={"domain": domain},
            )

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user, tenant=tenant)

        # Return tenant-aware tokens immediately (same claim set as login)
        refresh = RefreshToken.for_user(user)
        refresh["tenant_id"] = tenant.id
        refresh["tenant_name"] = tenant.name

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "tenant": tenant.name,
        }, status=201)
