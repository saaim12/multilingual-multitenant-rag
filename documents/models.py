from django.db import models
from pgvector.django import VectorField
from django.contrib.auth.models import User

class Tenant(models.Model):
    """One customer/organization. All data is scoped to a tenant."""
    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    api_quota = models.IntegerField(default=1000)
    requests_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DocumentChunk(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # isolation key
    source = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    embedding = VectorField(dimensions=768)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["tenant"])]

    def __str__(self):
        return f"[{self.tenant.name}] {self.content[:50]}"
    
class UserProfile(models.Model):
    """Links a Django login user to one tenant."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} → {self.tenant.name}"