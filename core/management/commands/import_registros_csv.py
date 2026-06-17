from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.db_utils import import_csv_to_database


class Command(BaseCommand):
    help = "Importa output/registros.csv para a tabela ProductionEntry no SQLite."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(Path(settings.BASE_DIR) / "output" / "registros.csv"),
            help="Caminho do CSV a ser importado.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["path"]).resolve()
        if not csv_path.exists():
            raise CommandError(f"Arquivo nao encontrado: {csv_path}")

        created, skipped = import_csv_to_database(csv_path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Importacao concluida. Criados: {created}. Ignorados: {skipped}."
            )
        )
