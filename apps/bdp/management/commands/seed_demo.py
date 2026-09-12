"""
Peuple une BDP + BDC de demonstration, alignee sur les exemples du mockup
theme-final.html, pour tester les ecrans du Panel de bout en bout.

Idempotent : relancer la commande vide et recree les donnees de demo
(reconnues par le flag `demo=True` implicite via reference_externe).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bdc.models import ActifClient, HistoriqueTraitement, Traitement
from apps.bdp.models import Renseignement
from apps.matching.services import calculer_matching


class Command(BaseCommand):
    help = "Peuple des donnees de demonstration (BDP + BDC) pour tester le Panel."

    def handle(self, *args, **options):
        now = timezone.now()

        self.stdout.write("Nettoyage des donnees de demo existantes...")
        Renseignement.objects.all().delete()
        Traitement.objects.all().delete()
        ActifClient.objects.all().delete()

        # --- Actifs / referentiels declares par le client ---
        actif_win = ActifClient.objects.create(
            type="technique", categorie="Systeme d'exploitation", editeur="Microsoft", produit="Windows 11", version="26100"
        )
        actif_palo = ActifClient.objects.create(
            type="technique", categorie="Pare-feu", editeur="Palo Alto Networks", produit="PAN-OS", version="11.1.2"
        )
        actif_python = ActifClient.objects.create(
            type="technique", categorie="Langage / runtime", editeur="Python Software Foundation", produit="Python", version="3.12.7"
        )
        actif_nis2 = ActifClient.objects.create(type="normatif", referentiel="NIS2")
        actif_iso = ActifClient.objects.create(type="normatif", referentiel="ISO 27001")

        # --- Renseignements BDP ---
        r_win_cve = Renseignement.objects.create(
            type="technique",
            titre="Windows 11 — exécution de code à distance",
            description=(
                "Use-after-free dans le composant de rendu, exécution de code arbitraire "
                "à distance sans interaction utilisateur. CVSS 9.8."
            ),
            source="NVD",
            reference_externe="CVE-2026-41823",
            criticite="critique",
            taxonomie_editeur="Microsoft",
            taxonomie_produit="Windows 11",
            taxonomie_version="26100",
            decouvert_le=now - timedelta(hours=2),
            cvss_score=9.8,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        )
        r_win_bulletin = Renseignement.objects.create(
            type="technique",
            titre="Bulletin Microsoft — pilote graphique tiers",
            description="Un pilote graphique tiers optionnel présente une faille d'élévation de privilèges locaux.",
            source="Microsoft Security Response Center",
            criticite="elevee",
            taxonomie_editeur="Microsoft",
            taxonomie_produit="Windows 11",
            decouvert_le=now - timedelta(hours=5),
        )
        r_palo = Renseignement.objects.create(
            type="technique",
            titre="Auth bypass — Palo Alto PAN-OS",
            description=(
                "Un contournement d'authentification permet un accès à l'interface "
                "d'administration sans identifiants valides. Correctif disponible."
            ),
            source="CERT-FR",
            criticite="elevee",
            taxonomie_editeur="Palo Alto Networks",
            taxonomie_produit="PAN-OS",
            decouvert_le=now - timedelta(hours=6),
            cvss_score=8.1,
            cvss_vector="CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N",
        )
        r_nis2 = Renseignement.objects.create(
            type="normatif",
            titre="NIS2 — périmètre entités importantes",
            description="Une nouvelle FAQ de l'ANSSI précise les critères de qualification des entités importantes pour le secteur numérique.",
            source="ANSSI",
            criticite="moyenne",
            taxonomie_referentiel="NIS2",
            decouvert_le=now - timedelta(days=1),
        )
        r_iso = Renseignement.objects.create(
            type="normatif",
            titre="ISO 27001 — révision Annexe A",
            description="Clarification éditoriale du contrôle A.5.7, sans changement des exigences de fond.",
            source="ISO",
            criticite="moyenne",
            taxonomie_referentiel="ISO 27001",
            decouvert_le=now - timedelta(days=3),
        )
        r_python = Renseignement.objects.create(
            type="technique",
            titre="Python — publication sécurité 3.12.7",
            description="Correctif d'une vulnérabilité de déni de service dans le module de parsing XML standard.",
            source="python.org",
            criticite="moyenne",
            taxonomie_editeur="Python Software Foundation",
            taxonomie_produit="Python",
            decouvert_le=now - timedelta(days=4),
        )

        # --- Traitements (statuts varies, comme dans le mockup) ---
        def _traiter(renseignement, actif, statut, justificatif="", heures_ecoulees=0):
            t = Traitement.objects.create(
                id_renseignement_bdp=renseignement.id_renseignement_bdp,
                actif=actif,
                statut=statut,
                justificatif=justificatif,
            )
            HistoriqueTraitement.objects.create(traitement=t, evenement="Découvert")
            if statut != "a_traiter":
                HistoriqueTraitement.objects.create(traitement=t, evenement="Pris en charge")
            if statut in ("clos", "non_applicable"):
                HistoriqueTraitement.objects.create(
                    traitement=t, evenement=t.get_statut_display()
                )
            return t

        _traiter(r_win_cve, actif_win, "a_traiter")
        _traiter(
            r_win_bulletin, actif_win, "non_applicable",
            justificatif="Pilote non déployé sur le parc — aucun actif concerné.",
        )
        _traiter(r_palo, actif_palo, "en_cours")
        _traiter(r_nis2, actif_nis2, "a_traiter")
        _traiter(
            r_iso, actif_iso, "clos",
            justificatif="Révision éditoriale du contrôle A.5.7, sans changement des exigences de fond — aucune action requise.",
        )
        _traiter(r_python, actif_python, "a_traiter")

        resultats = calculer_matching()

        self.stdout.write(self.style.SUCCESS(
            f"OK : {Renseignement.objects.count()} renseignements, "
            f"{ActifClient.objects.count()} actifs/référentiels, "
            f"{Traitement.objects.count()} traitements, "
            f"{len(resultats)} correspondances calculées par le Matching."
        ))
