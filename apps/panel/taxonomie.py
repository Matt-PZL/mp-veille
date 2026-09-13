"""
Taxonomie fournie pour la declaration d'actifs (brief section 3, methode 1 :
"Declaratif manuel : taxonomie fournie (categorie -> editeur -> produit),
le client coche" — pas de saisie libre).

Depuis l'ajout du catalogue automatique (apps.catalogue, alimente par
endoflife.date via apps.ingestion.tasks.collecter_catalogue_actifs), la
taxonomie n'est plus une liste figee tapee a la main : `taxonomie_technique()`
fusionne ce catalogue (~470 produits reels, rafraichis periodiquement) avec
un petit filet manuel ci-dessous, pour ne jamais regresser sur des entrees
deja utilisees si jamais le catalogue automatique ne les couvre pas encore.
"""

from apps.catalogue.models import ActifCatalogueProduit, ActifCatalogueVersion

TAXONOMIE_MANUELLE = {
    "Pare-feu / Réseau": {
        "Cisco": ["ASA", "Firepower Threat Defense"],
    },
    "Virtualisation / conteneurs": {
        "Proxmox Server Solutions": ["Proxmox VE"],
    },
    "Messagerie": {
        "Microsoft": ["Exchange Server", "Microsoft 365"],
        "Zimbra": ["Zimbra Collaboration Suite"],
    },
    "Applicatif web": {
        "Atlassian": ["Confluence", "Jira"],
    },
}

REFERENTIELS_NORMATIFS = [
    "ISO 27001",
    "ISO 27005",
    "NIS2",
    "RGPD",
    "DORA",
    "PCI DSS",
    "ANSSI — Guide d'hygiène informatique",
    "CNIL — Référentiel sécurité",
]


def taxonomie_technique() -> dict:
    """Categorie -> Editeur -> [produits], fusion du catalogue automatique
    (endoflife.date) et du filet manuel — recalcule a chaque appel (donnees
    vivantes en base, pas une liste Python figee a l'import)."""
    resultat: dict[str, dict[str, list[str]]] = {}

    for categorie, editeurs in TAXONOMIE_MANUELLE.items():
        for editeur, produits in editeurs.items():
            bucket = resultat.setdefault(categorie, {}).setdefault(editeur, [])
            for produit in produits:
                if produit not in bucket:
                    bucket.append(produit)

    for entree in ActifCatalogueProduit.objects.all().order_by("categorie", "editeur", "produit"):
        bucket = resultat.setdefault(entree.categorie, {}).setdefault(entree.editeur, [])
        if entree.produit not in bucket:
            bucket.append(entree.produit)

    return resultat


def versions_connues(max_par_produit: int = 15) -> dict:
    """produit -> [versions connues] (les plus recentes d'abord) — pour
    suggerer les versions disponibles a la saisie (Ajouter / Monter en
    version) au lieu d'un champ entierement libre."""
    resultat: dict[str, list[str]] = {}
    for v in ActifCatalogueVersion.objects.select_related("produit").order_by(
        "produit__produit", "-sortie_le", "-version"
    ):
        bucket = resultat.setdefault(v.produit.produit, [])
        if v.version not in bucket and len(bucket) < max_par_produit:
            bucket.append(v.version)
    return resultat
