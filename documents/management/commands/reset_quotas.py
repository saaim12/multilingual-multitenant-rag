from django.core.management.base import BaseCommand
from documents.models import Tenant


class Command(BaseCommand):
    help = "Reset requests_used to 0 for all tenants (run monthly)"

    def handle(self, *args, **options):
        updated = Tenant.objects.update(requests_used=0)
        self.stdout.write(self.style.SUCCESS(f"Reset quota counters for {updated} tenant(s)."))
