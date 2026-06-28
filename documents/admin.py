from django.contrib import admin
from documents.models import Tenant, DocumentChunk


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "api_quota", "requests_used", "created_at")
    search_fields = ("name",)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "category", "short_content", "source", "created_at")
    list_filter = ("tenant", "category", "source")   # sidebar filters
    search_fields = ("content",)

    def short_content(self, obj):
        """Show first 60 chars of content in the list (full text is huge)."""
        return obj.content[:60]
    short_content.short_description = "Content"

from documents.models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant")
    list_filter = ("tenant",)