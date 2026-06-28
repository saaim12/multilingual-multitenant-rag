from django.core.management.base import BaseCommand
from documents.services.ingestion import ingest_csv


class Command(BaseCommand):
    help = "Ingest a CSV file into the vector store under a given tenant"

    def add_arguments(self, parser):
        # positional argument: the CSV path
        parser.add_argument("file_path", type=str)
        # required option: which tenant this data belongs to
        parser.add_argument("--tenant", type=str, required=True,
                            help="Tenant name, e.g. 'Acme Translations'")

    def handle(self, *args, **options):
        path = options["file_path"]
        tenant_name = options["tenant"]

        self.stdout.write(f"Ingesting {path} for tenant '{tenant_name}' ...")
        count = ingest_csv(path, tenant_name)
        self.stdout.write(self.style.SUCCESS(
            f"Done. {count} chunks ingested for '{tenant_name}'."
        ))