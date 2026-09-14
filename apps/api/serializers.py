"""
Serialiseurs DRF — couche additive au-dessus des modeles existants (BDP/BDC/
catalogue). N'ecrit jamais dans la BDP (lecture seule, comme le reste de
l'app), respecte les memes frontieres que les vues Django historiques.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.bdc.models import ActifClient, HistoriqueActif, Traitement
from apps.bdp.models import Renseignement
from apps.catalogue.models import ActifCatalogueProduit, ActifCatalogueVersion
from apps.vitrine.models import MessageContact

User = get_user_model()


class InscriptionSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )


class RenseignementSerializer(serializers.ModelSerializer):
    reference_courte = serializers.ReadOnlyField()
    nature_display = serializers.CharField(source="get_nature_display", read_only=True)
    criticite_display = serializers.CharField(source="get_criticite_display", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    cvss_radar = serializers.SerializerMethodField()
    statut = serializers.SerializerMethodField()
    statut_display = serializers.SerializerMethodField()
    actif_lie = serializers.SerializerMethodField()

    class Meta:
        model = Renseignement
        fields = [
            "id_renseignement_bdp", "type", "type_display", "titre", "description",
            "source", "url_source", "reference_externe", "reference_courte",
            "criticite", "criticite_display", "nature", "nature_display",
            "cvss_score", "cvss_vector", "cvss_radar",
            "taxonomie_editeur", "taxonomie_produit", "taxonomie_referentiel",
            "decouvert_le", "statut", "statut_display", "actif_lie",
        ]

    def get_cvss_radar(self, obj):
        return obj.cvss_radar()

    def _traitement(self, obj):
        return self.context.get("traitements_par_id", {}).get(obj.id_renseignement_bdp)

    def get_statut(self, obj):
        t = self._traitement(obj)
        return t.statut if t else "a_traiter"

    def get_statut_display(self, obj):
        t = self._traitement(obj)
        return t.get_statut_display() if t else "À traiter"

    def get_actif_lie(self, obj):
        t = self._traitement(obj)
        return str(t.actif) if t and t.actif else None


class ActifClientSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    nb_traitements = serializers.IntegerField(source="traitements.count", read_only=True)

    class Meta:
        model = ActifClient
        fields = [
            "id", "type", "type_display", "categorie", "editeur", "produit",
            "version", "referentiel", "ajoute_le", "nb_traitements",
        ]


class TraitementSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    actif_nom = serializers.SerializerMethodField()
    renseignement = serializers.SerializerMethodField()

    class Meta:
        model = Traitement
        fields = [
            "id", "id_renseignement_bdp", "actif", "actif_nom", "statut", "statut_display",
            "justificatif", "echeance", "plan_action", "passage_cab", "en_retard",
            "maj_le", "renseignement",
        ]

    def get_actif_nom(self, obj):
        return str(obj.actif) if obj.actif else None

    def get_renseignement(self, obj):
        r = self.context.get("renseignements_par_id", {}).get(obj.id_renseignement_bdp)
        if not r:
            return None
        return {
            "titre": r.titre,
            "reference_courte": r.reference_courte,
            "criticite": r.criticite,
            "source": r.source,
        }


class HistoriqueActifSerializer(serializers.ModelSerializer):
    evenement_display = serializers.CharField(source="get_evenement_display", read_only=True)

    class Meta:
        model = HistoriqueActif
        fields = ["actif_repr", "evenement", "evenement_display", "detail", "horodatage"]


class ActifCatalogueVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActifCatalogueVersion
        fields = ["version", "label", "maintenue", "sortie_le"]


class ActifCatalogueProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActifCatalogueProduit
        fields = ["id", "categorie", "editeur", "produit"]


class MessageContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageContact
        fields = ["nom", "email", "entreprise", "message"]
