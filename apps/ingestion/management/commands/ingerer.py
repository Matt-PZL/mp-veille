"""
Declenche un cycle d'ingestion (ou une seule source) a la demande, sans
attendre le cron 12h — utile pour tester une source apres modification, ou
rattraper un cycle manque.

Les taches restent de simples fonctions Python (@shared_task sans .delay()) :
appelables directement en synchrone, aucun broker/worker requis.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.tasks import (
    collecter_catalogue_actifs,
    collecter_cert_fr_alertes,
    collecter_cert_fr_avis,
    collecter_nvd_cve,
    collecter_referentiels_normatifs,
    cycle_ingestion,
    enrichir_kev,
)

_SOURCES = {
    "nvd": collecter_nvd_cve,
    "kev": enrichir_kev,
    "cert_fr_avis": collecter_cert_fr_avis,
    "cert_fr_alertes": collecter_cert_fr_alertes,
    "cnil": collecter_referentiels_normatifs,
    "catalogue": collecter_catalogue_actifs,
}


class Command(BaseCommand):
    help = "Declenche l'ingestion (toutes les sources, ou --source <nom>) sans attendre le cron 12h."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=sorted(_SOURCES),
            help=f"Ne collecter qu'une source ({', '.join(sorted(_SOURCES))}). Omis : cycle complet.",
        )

    def handle(self, *args, **options):
        source = options.get("source")
        if source:
            self.stdout.write(f"Collecte : {source}...")
            resultat = _SOURCES[source]()
            self.stdout.write(self.style.SUCCESS(f"Termine : {resultat}"))
            return

        self.stdout.write("Cycle d'ingestion complet...")
        cycle_ingestion()
        self.stdout.write(self.style.SUCCESS("Cycle termine."))
