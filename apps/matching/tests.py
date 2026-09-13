"""
Tests du moteur de Matching.

Les cas viennent de donnees reellement observees en base apres un cycle de
collecte (NVD, CERT-FR, CNIL) : c'est la nomenclature de ces sources qui
faisait echouer la correspondance exacte de la V1.
"""

from django.test import TestCase
from django.utils import timezone

from apps.bdc.models import ActifClient
from apps.bdp.models import Renseignement

from .normalisation import (
    canoniser_editeur,
    canoniser_produit,
    canoniser_referentiel,
    est_vide,
    normaliser,
    tokens_distinctifs,
)
from .services import (
    CONFIANCE_EXACTE,
    CONFIANCE_INCLUSION,
    CONFIANCE_PRODUIT,
    CONFIANCE_TITRE,
    calculer_matching,
)


class NormalisationTest(TestCase):
    def test_normaliser_retire_accents_casse_ponctuation(self):
        self.assertEqual(normaliser("Palo Alto Networks, Inc."), "palo alto networks inc")
        self.assertEqual(normaliser("Réseau — Élevée"), "reseau elevee")
        self.assertEqual(normaliser("PAN-OS"), "pan os")
        self.assertEqual(normaliser(None), "")

    def test_canoniser_editeur_retire_suffixes_corporatifs(self):
        self.assertEqual(canoniser_editeur("Red Hat, Inc."), "red hat")
        self.assertEqual(canoniser_editeur("Cisco Systems, Inc."), "cisco")
        self.assertEqual(canoniser_editeur("The Apache Software Foundation"), "apache")

    def test_canoniser_editeur_applique_les_alias(self):
        self.assertEqual(canoniser_editeur("Palo Alto Networks"), "palo alto")
        self.assertEqual(canoniser_editeur("paloaltonetworks"), "palo alto")
        self.assertEqual(canoniser_editeur("Canonical"), "ubuntu")

    def test_canoniser_produit_applique_les_alias(self):
        self.assertEqual(canoniser_produit("RHEL"), "red hat enterprise linux")
        self.assertEqual(canoniser_produit("PAN-OS"), "pan os")
        self.assertEqual(canoniser_produit("Exchange Server"), "exchange")

    def test_canoniser_referentiel_unifie_les_variantes(self):
        self.assertEqual(canoniser_referentiel("GDPR"), "rgpd")
        self.assertEqual(canoniser_referentiel("ISO/IEC 27001"), "iso 27001")
        self.assertEqual(canoniser_referentiel("NIS 2"), "nis2")

    def test_valeurs_de_remplissage_traitees_comme_vides(self):
        # Le CERT-FR renseigne « N/A » quand l'avis ne cible pas un produit.
        self.assertTrue(est_vide("N/A"))
        self.assertTrue(est_vide(""))
        self.assertFalse(est_vide("Exchange"))
        self.assertEqual(canoniser_produit("N/A"), "")

    def test_tokens_distinctifs_retire_les_mots_generiques(self):
        self.assertEqual(tokens_distinctifs("Exchange Server"), frozenset({"exchange"}))
        # Un nom entierement generique conserve ses mots plutot que de devenir
        # vide (un ensemble vide matcherait n'importe quel titre).
        self.assertEqual(tokens_distinctifs("Server"), frozenset({"server"}))


class MatchingTechniqueTest(TestCase):
    def _rens(self, **kwargs):
        defaults = {
            "type": "technique",
            "titre": "Titre",
            "description": "Description",
            "source": "TEST",
            "decouvert_le": timezone.now(),
        }
        return Renseignement.objects.create(**{**defaults, **kwargs})

    def test_correspondance_exacte(self):
        actif = ActifClient.objects.create(
            type="technique", editeur="Cisco", produit="Firepower Threat Defense"
        )
        r = self._rens(taxonomie_editeur="Cisco", taxonomie_produit="Firepower Threat Defense")

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.renseignement, r)
        self.assertEqual(resultat.confiance, CONFIANCE_EXACTE)
        self.assertEqual(resultat.palier, "exact")

    def test_casse_accents_et_ponctuation_ignores(self):
        """Le cas qui echouait en V1 : meme produit, orthographe differente."""
        actif = ActifClient.objects.create(
            type="technique", editeur="Palo Alto Networks", produit="PAN-OS"
        )
        self._rens(taxonomie_editeur="paloaltonetworks", taxonomie_produit="panos")

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_EXACTE)

    def test_alias_produit_courant(self):
        """Le client tape « RHEL », la source ecrit le nom complet."""
        actif = ActifClient.objects.create(type="technique", editeur="Red Hat", produit="RHEL")
        self._rens(
            taxonomie_editeur="Red Hat, Inc.", taxonomie_produit="Red Hat Enterprise Linux"
        )

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_EXACTE)

    def test_editeur_absent_cote_source(self):
        actif = ActifClient.objects.create(type="technique", editeur="Cisco", produit="FTD")
        self._rens(taxonomie_editeur="", taxonomie_produit="Firepower Threat Defense")

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_PRODUIT)
        self.assertEqual(resultat.palier, "produit")

    def test_inclusion_de_noms(self):
        """« Firepower Threat Defense » dans « Cisco Firepower Threat Defense »."""
        actif = ActifClient.objects.create(
            type="technique", editeur="Cisco", produit="Firepower Threat Defense"
        )
        self._rens(
            taxonomie_editeur="Cisco", taxonomie_produit="Cisco Firepower Threat Defense"
        )

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_INCLUSION)
        self.assertEqual(resultat.palier, "inclusion")

    def test_repli_sur_le_titre_quand_la_source_ne_nomme_pas_le_produit(self):
        """Cas CERT-FR reel : editeur « Microsoft », produit « N/A », le nom
        du produit n'apparait que dans le titre de l'avis."""
        actif = ActifClient.objects.create(
            type="technique", editeur="Microsoft", produit="Exchange Server"
        )
        self._rens(
            titre="Multiples vulnérabilités dans Microsoft Exchange",
            taxonomie_editeur="Microsoft",
            taxonomie_produit="N/A",
        )

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_TITRE)
        self.assertEqual(resultat.palier, "titre")

    def test_editeurs_differents_ne_matchent_pas(self):
        """Deux « Commerce » d'editeurs distincts ne doivent pas se confondre."""
        actif = ActifClient.objects.create(type="technique", editeur="Adobe", produit="Commerce")
        self._rens(taxonomie_editeur="Oracle", taxonomie_produit="Commerce")

        self.assertEqual(calculer_matching([actif]), [])

    def test_produit_different_ne_matche_pas(self):
        actif = ActifClient.objects.create(
            type="technique", editeur="Microsoft", produit="Exchange Server"
        )
        self._rens(taxonomie_editeur="Microsoft", taxonomie_produit="SharePoint")

        self.assertEqual(calculer_matching([actif]), [])

    def test_titre_sans_le_produit_ne_matche_pas(self):
        actif = ActifClient.objects.create(
            type="technique", editeur="Microsoft", produit="Exchange Server"
        )
        self._rens(
            titre="Multiples vulnérabilités dans Microsoft SharePoint",
            taxonomie_editeur="Microsoft",
            taxonomie_produit="N/A",
        )

        self.assertEqual(calculer_matching([actif]), [])

    def test_actif_sans_produit_ignore(self):
        actif = ActifClient.objects.create(type="technique", editeur="Microsoft", produit="")
        self._rens(taxonomie_editeur="Microsoft", taxonomie_produit="Exchange")

        self.assertEqual(calculer_matching([actif]), [])

    def test_un_renseignement_normatif_ne_matche_pas_un_actif_technique(self):
        actif = ActifClient.objects.create(
            type="technique", editeur="Microsoft", produit="Exchange"
        )
        self._rens(type="normatif", taxonomie_editeur="Microsoft", taxonomie_produit="Exchange")

        self.assertEqual(calculer_matching([actif]), [])

    def test_pas_de_doublon_pour_un_meme_couple(self):
        actif = ActifClient.objects.create(
            type="technique", editeur="Microsoft", produit="Exchange"
        )
        self._rens(
            titre="Vulnérabilité dans Microsoft Exchange",
            taxonomie_editeur="Microsoft",
            taxonomie_produit="Exchange",
        )

        resultats = calculer_matching([actif])
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].confiance, CONFIANCE_EXACTE)

    def test_tri_par_confiance_decroissante(self):
        actif = ActifClient.objects.create(
            type="technique", editeur="Microsoft", produit="Exchange Server"
        )
        self._rens(
            titre="Avis sur Microsoft Exchange",
            taxonomie_editeur="Microsoft",
            taxonomie_produit="N/A",
        )
        exact = self._rens(taxonomie_editeur="Microsoft", taxonomie_produit="Exchange Server")

        resultats = calculer_matching([actif])
        self.assertEqual(len(resultats), 2)
        self.assertEqual(resultats[0].renseignement, exact)
        self.assertGreater(resultats[0].confiance, resultats[1].confiance)


class MatchingNormatifTest(TestCase):
    def _rens(self, **kwargs):
        defaults = {
            "type": "normatif",
            "titre": "Titre",
            "description": "Description",
            "source": "TEST",
            "decouvert_le": timezone.now(),
        }
        return Renseignement.objects.create(**{**defaults, **kwargs})

    def test_alias_referentiel(self):
        """Le client declare « GDPR », la CNIL tague « RGPD »."""
        actif = ActifClient.objects.create(type="normatif", referentiel="GDPR")
        self._rens(taxonomie_referentiel="RGPD")

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_EXACTE)

    def test_variante_iso(self):
        actif = ActifClient.objects.create(type="normatif", referentiel="ISO/IEC 27001")
        self._rens(taxonomie_referentiel="ISO 27001")

        (resultat,) = calculer_matching([actif])
        self.assertEqual(resultat.confiance, CONFIANCE_EXACTE)

    def test_referentiel_different_ne_matche_pas(self):
        actif = ActifClient.objects.create(type="normatif", referentiel="RGPD")
        self._rens(taxonomie_referentiel="NIS2")

        self.assertEqual(calculer_matching([actif]), [])

    def test_actif_sans_referentiel_ignore(self):
        actif = ActifClient.objects.create(type="normatif", referentiel="")
        self._rens(taxonomie_referentiel="RGPD")

        self.assertEqual(calculer_matching([actif]), [])


class MatchingLectureSeuleTest(TestCase):
    """Le Matching ne doit JAMAIS ecrire (brief section 2)."""

    def test_aucune_ecriture_en_base(self):
        from apps.bdc.models import Traitement

        actif = ActifClient.objects.create(
            type="technique", editeur="Cisco", produit="Firepower Threat Defense"
        )
        Renseignement.objects.create(
            type="technique",
            titre="T",
            description="D",
            source="TEST",
            decouvert_le=timezone.now(),
            taxonomie_editeur="Cisco",
            taxonomie_produit="Firepower Threat Defense",
        )

        avant = (
            ActifClient.objects.count(),
            Renseignement.objects.count(),
            Traitement.objects.count(),
        )
        calculer_matching([actif])
        apres = (
            ActifClient.objects.count(),
            Renseignement.objects.count(),
            Traitement.objects.count(),
        )
        self.assertEqual(avant, apres)
