import math
import uuid

from django.db import models


class Renseignement(models.Model):
    """
    Un renseignement de la BDP : le moment ou un renseignement public (CVE,
    bulletin CERT-FR, texte normatif...) devient un actif propriétaire.

    Jamais ecrase : si la source evolue (CVSS revise, texte amende), on cree
    une nouvelle version liee a l'original via `parent` plutot que de modifier
    en place (tracabilite = preuve d'audit).
    """

    TYPE_CHOICES = [
        ("technique", "Technique"),
        ("normatif", "Normatif"),
    ]
    CRITICITE_CHOICES = [
        ("critique", "Critique"),
        ("elevee", "Élevée"),
        ("moyenne", "Moyenne"),
        ("faible", "Faible"),
    ]
    # Nature du renseignement — un CVE brut n'appelle pas la meme reponse
    # qu'un bulletin qui annonce deja le correctif, ou qu'une simple
    # clarification editoriale d'un referentiel : ce champ porte cette
    # distinction independamment de la criticite/severite.
    NATURE_CHOICES = [
        ("vulnerabilite", "Vulnérabilité"),
        ("correctif", "Correctif"),
        ("reglementaire", "Réglementaire"),
        ("information", "Information"),
    ]

    id_renseignement_bdp = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="versions"
    )

    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=500)
    description = models.TextField()

    source = models.CharField(max_length=200, help_text="ex: NVD, CERT-FR, ANSSI, ISO")
    url_source = models.URLField(
        max_length=500, blank=True, help_text="Lien vers l'avis/l'article d'origine, pour verification"
    )
    reference_externe = models.CharField(
        max_length=200, blank=True, help_text="ex: CVE-2026-41823"
    )
    criticite = models.CharField(max_length=16, choices=CRITICITE_CHOICES, blank=True)
    nature = models.CharField(max_length=16, choices=NATURE_CHOICES, blank=True)

    # Detail CVSS (technique uniquement) — vecteur brut + score, pour affichage
    # d'une analyse d'exploitabilite/impact dans le detail du renseignement.
    cvss_score = models.FloatField(null=True, blank=True)
    cvss_vector = models.CharField(max_length=100, blank=True, help_text="ex: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")

    # Enrichissement complementaire — rempli par l'ingestion quand la source
    # le fournit (KEV alimente tags/niveau_confiance/cve_associees ; les
    # autres restent vides tant qu'aucune source ne les couvre). Jamais
    # obligatoires, toujours affiches conditionnellement cote front.
    AUTEUR_TLP = [
        ("clear", "TLP:CLEAR"),
        ("green", "TLP:GREEN"),
        ("amber", "TLP:AMBER"),
        ("red", "TLP:RED"),
    ]
    NIVEAU_CONFIANCE_CHOICES = [
        ("faible", "Faible"),
        ("moyen", "Moyen"),
        ("eleve", "Élevé"),
    ]
    auteur = models.CharField(max_length=200, blank=True, help_text="Analyste ou organisme auteur, si distinct de la source")
    niveau_confiance = models.CharField(max_length=16, choices=NIVEAU_CONFIANCE_CHOICES, blank=True)
    tags = models.JSONField(default=list, blank=True, help_text="Mots-cles libres, ex: ['ransomware', 'KEV']")
    secteur_concerne = models.CharField(max_length=200, blank=True, help_text="Secteur vise, si la source le precise")
    tlp = models.CharField(max_length=8, choices=AUTEUR_TLP, blank=True, help_text="Traffic Light Protocol")
    cve_associees = models.JSONField(default=list, blank=True, help_text="CVE additionnelles au-dela de reference_externe")
    ioc_associees = models.JSONField(default=list, blank=True, help_text="Indicateurs de compromission (hash, IP, domaine...)")

    # Taxonomie de rattachement — cle de lecture pour le Matching (non sensible).
    # Volet technique : categorie > editeur > produit > version.
    taxonomie_categorie = models.CharField(max_length=200, blank=True)
    taxonomie_editeur = models.CharField(max_length=200, blank=True)
    taxonomie_produit = models.CharField(max_length=200, blank=True)
    taxonomie_version = models.CharField(max_length=100, blank=True)
    # Volet normatif : referentiel (+ article/exigence en texte libre pour l'instant).
    taxonomie_referentiel = models.CharField(max_length=200, blank=True)

    decouvert_le = models.DateTimeField()
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decouvert_le"]
        indexes = [
            models.Index(fields=["taxonomie_editeur", "taxonomie_produit"]),
            models.Index(fields=["taxonomie_referentiel"]),
        ]
        constraints = [
            # Garde-fou base contre le doublon exact : deux ecritures pour la
            # meme source + meme reference + meme revision source ne peuvent
            # plus coexister, meme en cas de course entre deux runs
            # d'ingestion concurrents. Le versionning legitime (parent) reste
            # possible : une revision differente change `decouvert_le`.
            models.UniqueConstraint(
                fields=["source", "reference_externe", "decouvert_le"],
                name="renseignement_source_ref_revision_unique",
            ),
        ]

    def __str__(self):
        return f"{self.titre} ({self.id_renseignement_bdp})"

    @property
    def reference_courte(self):
        """Reference a afficher a l'utilisateur. En interne, certaines sources
        (CERT-FR) ont besoin d'une reference_externe composee (`AVIS::produit`)
        pour que chaque couple avis/produit reste identifie de facon unique
        sans casser le versionning — mais cette partie technique ne doit
        jamais fuiter dans l'UI, seule la reference publique (avant `::`)
        a du sens pour un humain."""
        return self.reference_externe.split("::", 1)[0]

    _CVSS_LABELS = {
        "AV": {"N": "Réseau", "A": "Adjacent", "L": "Local", "P": "Physique"},
        "AC": {"L": "Faible", "H": "Élevée"},
        "PR": {"N": "Aucun", "L": "Faible", "H": "Élevé"},
        "UI": {"N": "Aucune", "R": "Requise"},
        "S": {"U": "Inchangée", "C": "Modifiée"},
        "C": {"N": "Aucun", "L": "Faible", "H": "Élevé"},
        "I": {"N": "Aucun", "L": "Faible", "H": "Élevé"},
        "A": {"N": "Aucun", "L": "Faible", "H": "Élevé"},
    }
    _CVSS_FIELD_LABELS = {
        "AV": "Vecteur d'accès", "AC": "Complexité", "PR": "Privilèges requis", "UI": "Interaction",
        "S": "Portée", "C": "Confidentialité", "I": "Intégrité", "A": "Disponibilité",
    }

    def cvss_details(self):
        """Decode le vecteur CVSS brut en libelles lisibles pour l'affichage
        (exploitabilite + impact), a la maniere d'un rapport d'analyse."""
        if not self.cvss_vector:
            return None
        parts = dict(
            p.split(":", 1) for p in self.cvss_vector.split("/") if ":" in p
        )
        details = []
        for code in ("AV", "AC", "PR", "UI", "S", "C", "I", "A"):
            valeur = parts.get(code)
            if valeur is None:
                continue
            details.append({
                "code": code,
                "champ": self._CVSS_FIELD_LABELS.get(code, code),
                "valeur": self._CVSS_LABELS.get(code, {}).get(valeur, valeur),
            })
        return details

    # Severite normalisee par axe (0 = benin, 1 = pire cas) — sert uniquement
    # a dessiner la forme du radar, pas une donnee CVSS officielle.
    _CVSS_AXIS_SEVERITE = {
        "AV": {"N": 1.0, "A": 0.66, "L": 0.33, "P": 0.0},
        "AC": {"L": 1.0, "H": 0.33},
        "PR": {"N": 1.0, "L": 0.66, "H": 0.33},
        "UI": {"N": 1.0, "R": 0.33},
        "S": {"C": 1.0, "U": 0.33},
        "C": {"H": 1.0, "L": 0.5, "N": 0.0},
        "I": {"H": 1.0, "L": 0.5, "N": 0.0},
        "A": {"H": 1.0, "L": 0.5, "N": 0.0},
    }
    _CVSS_AXIS_ORDER = ("AV", "AC", "PR", "UI", "S", "C", "I", "A")

    def cvss_radar(self, cx=110, cy=110, r=64):
        """Precalcule les coordonnees SVG d'un radar CVSS a 8 axes (les
        gabarits Django ne font pas de trigonometrie) : polygone de valeurs,
        grille de fond, et position de chaque etiquette d'axe."""
        if not self.cvss_vector:
            return None
        parts = dict(p.split(":", 1) for p in self.cvss_vector.split("/") if ":" in p)
        n = len(self._CVSS_AXIS_ORDER)

        points, grid_points, axes = [], [], []
        for i, code in enumerate(self._CVSS_AXIS_ORDER):
            angle = -math.pi / 2 + i * (2 * math.pi / n)
            cos_a, sin_a = math.cos(angle), math.sin(angle)

            valeur = parts.get(code)
            sev = self._CVSS_AXIS_SEVERITE.get(code, {}).get(valeur, 0.0)
            rr = r * (0.14 + 0.86 * sev)

            points.append(f"{cx + rr * cos_a:.1f},{cy + rr * sin_a:.1f}")
            gx, gy = cx + r * cos_a, cy + r * sin_a
            grid_points.append(f"{gx:.1f},{gy:.1f}")

            lx, ly = cx + (r + 30) * cos_a, cy + (r + 30) * sin_a
            anchor = "middle" if abs(cos_a) < 0.2 else ("start" if cos_a > 0 else "end")
            axes.append({
                "label": self._CVSS_FIELD_LABELS.get(code, code),
                "valeur": self._CVSS_LABELS.get(code, {}).get(valeur, valeur or "—"),
                "sx": round(gx, 1), "sy": round(gy, 1),
                "x": round(lx, 1), "y": round(ly, 1),
                "anchor": anchor,
            })

        return {
            "points": " ".join(points),
            "grid_points": " ".join(grid_points),
            "axes": axes,
            "cx": cx, "cy": cy,
        }
