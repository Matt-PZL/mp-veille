"""
Contexte injecte dans tous les gabarits pour le rail de navigation permanent.

Volontairement limite a des COUNT/MAX SQL : le rail s'affiche sur chaque page,
il ne doit jamais declencher un calcul de Matching (qui parcourt la BDP).
"""

from apps.bdc.models import ActifClient, Traitement
from apps.bdp.models import Renseignement


def rail(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "rail_nb_actifs": ActifClient.objects.count(),
        "rail_nb_traitements": Traitement.objects.count(),
        "rail_nb_a_traiter": Traitement.objects.filter(statut="a_traiter").count(),
        "rail_derniere_collecte": Renseignement.objects.order_by("-cree_le")
        .values_list("cree_le", flat=True)
        .first(),
    }
