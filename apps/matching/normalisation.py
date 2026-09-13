"""
Normalisation et alias de noms d'editeurs / produits / referentiels.

Raison d'etre : chaque source nomme les choses a sa facon. Pour un meme
pare-feu Palo Alto, on trouve « PAN-OS » chez l'editeur, « Palo Alto Networks
PAN-OS » chez NVD, et « PAN-OS » sous l'editeur « Palo Alto Networks » au
CERT-FR — et le client, lui, a tape ce qu'il voulait. Une comparaison de
chaines exacte ne matche donc quasiment jamais en dehors du cas ou c'est
nous-memes qui avons ecrit la taxonomie (cf. collecter_nvd_cve, qui recopie
le nom de l'actif du client : un matching exact y « reussit » artificiellement).

Ce module ne fait que du texte : aucun acces base, aucun effet de bord.
"""

from __future__ import annotations

import re
import unicodedata

# Suffixes corporatifs : « Red Hat, Inc. » et « Red Hat » designent le meme
# editeur. Retires uniquement des noms d'EDITEUR, jamais des produits (ou
# « Project » peut etre signifiant, ex. « Fedora Project » en tant que produit).
_BRUIT_EDITEUR = frozenset({
    "inc", "llc", "ltd", "limited", "corp", "corporation", "co", "company",
    "sa", "sas", "sarl", "gmbh", "bv", "ab", "plc", "oy", "as",
    "foundation", "project", "software", "systems", "technologies", "technology",
    "group", "labs", "the", "and", "of",
})

# Mots trop generiques pour porter a eux seuls l'identite d'un produit. Ils ne
# sont retires que pour la recherche dans les titres d'avis : le CERT-FR titre
# « Multiples vulnerabilites dans Microsoft Exchange » la ou le client a
# declare « Exchange Server ». Exiger « server » ferait rater l'avis.
_BRUIT_PRODUIT = frozenset({
    "server", "serveur", "edition", "os", "software", "suite", "platform",
    "plateforme", "system", "systeme", "service", "services", "client",
})

# Alias d'EDITEURS : forme normalisee -> forme canonique normalisee.
_ALIAS_EDITEUR = {
    "paloalto": "palo alto",
    "paloaltonetworks": "palo alto",
    "palo alto networks": "palo alto",
    "microsoft corporation": "microsoft",
    "msft": "microsoft",
    "redhat": "red hat",
    "rhel": "red hat",
    "canonical": "ubuntu",
    "debian project": "debian",
    "oracle corporation": "oracle",
    "sun microsystems": "oracle",
    "mysql ab": "oracle",
    "vmware by broadcom": "vmware",
    "broadcom": "vmware",
    "cisco systems": "cisco",
    "check point": "checkpoint",
    "check point software": "checkpoint",
    "fortinet": "fortinet",
    "apache": "apache",
    "apache software": "apache",
    "the apache software foundation": "apache",
    "postgresql global development": "postgresql",
    "python software": "python",
    "nodejs": "node",
    "node js": "node",
    "hewlett packard": "hp",
    "hewlett packard enterprise": "hpe",
    "hpe": "hpe",
    "ibm corporation": "ibm",
    "elasticsearch": "elastic",
    "atlassian corporation": "atlassian",
    "gitlab": "gitlab",
    "f5 networks": "f5",
    "juniper networks": "juniper",
    "sonicwall": "sonicwall",
    "trend micro": "trendmicro",
}

# Alias de PRODUITS : forme normalisee -> forme canonique normalisee.
# Sert surtout aux noms courts que les professionnels emploient au quotidien
# (« RHEL », « ESXi ») face aux noms longs des sources officielles.
_ALIAS_PRODUIT = {
    "panos": "pan os",
    "pan os": "pan os",
    "rhel": "red hat enterprise linux",
    "red hat enterprise linux server": "red hat enterprise linux",
    "esxi": "vmware esxi",
    "vsphere esxi": "vmware esxi",
    "win server": "windows server",
    "windows srv": "windows server",
    "ms exchange": "exchange",
    "exchange server": "exchange",
    "microsoft exchange server": "exchange",
    "sql server": "microsoft sql server",
    "mssql": "microsoft sql server",
    "ftd": "firepower threat defense",
    "cisco ftd": "firepower threat defense",
    "asa": "adaptive security appliance",
    "fortios": "fortios",
    "forti os": "fortios",
    "apache http server": "apache httpd",
    "httpd": "apache httpd",
    "apache http": "apache httpd",
    "postgres": "postgresql",
    "node js": "node js",
    "nodejs": "node js",
    "k8s": "kubernetes",
    "ad": "active directory",
    "o365": "microsoft 365",
    "office 365": "microsoft 365",
}

# Alias de REFERENTIELS normatifs.
_ALIAS_REFERENTIEL = {
    "gdpr": "rgpd",
    "reglement general sur la protection des donnees": "rgpd",
    "iso iec 27001": "iso 27001",
    "iso27001": "iso 27001",
    "iso 27 001": "iso 27001",
    "iso iec 27002": "iso 27002",
    "iso27002": "iso 27002",
    "nis 2": "nis2",
    "directive nis2": "nis2",
    "nis ii": "nis2",
    "dora": "dora",
    "reglement dora": "dora",
    "pci dss": "pci dss",
    "pcidss": "pci dss",
    "hds": "hds",
    "secnumcloud": "secnumcloud",
}

# Valeurs de remplissage que certaines sources mettent a la place d'un produit
# reel (le CERT-FR renseigne « N/A » quand l'avis ne cible pas un produit).
_VALEURS_VIDES = frozenset({"", "n a", "na", "non applicable", "unknown", "inconnu", "autre"})


def normaliser(texte: str | None) -> str:
    """Minuscules, sans accents, sans ponctuation, espaces normalises.

    « Palo Alto Networks, Inc. » et « palo-alto networks inc » donnent tous
    deux « palo alto networks inc ».
    """
    if not texte:
        return ""
    texte = unicodedata.normalize("NFKD", str(texte))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.lower()
    texte = re.sub(r"[^a-z0-9]+", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def est_vide(texte: str | None) -> bool:
    """Vrai si la valeur ne porte aucune information exploitable — chaine
    vide, ou remplissage de source type « N/A »."""
    return normaliser(texte) in _VALEURS_VIDES


def canoniser_editeur(nom: str | None) -> str:
    """Forme canonique d'un nom d'editeur : normalise, desuffixe, alias applique."""
    base = normaliser(nom)
    if base in _VALEURS_VIDES:
        return ""
    if base in _ALIAS_EDITEUR:
        return _ALIAS_EDITEUR[base]
    sans_bruit = " ".join(m for m in base.split() if m not in _BRUIT_EDITEUR)
    # L'alias peut ne matcher qu'apres retrait des suffixes corporatifs
    # (« Cisco Systems, Inc. » -> « cisco systems » -> « cisco »).
    return _ALIAS_EDITEUR.get(sans_bruit, sans_bruit or base)


def canoniser_produit(nom: str | None) -> str:
    """Forme canonique d'un nom de produit : normalise puis alias applique."""
    base = normaliser(nom)
    if base in _VALEURS_VIDES:
        return ""
    return _ALIAS_PRODUIT.get(base, base)


def canoniser_referentiel(nom: str | None) -> str:
    """Forme canonique d'un referentiel normatif."""
    base = normaliser(nom)
    if base in _VALEURS_VIDES:
        return ""
    return _ALIAS_REFERENTIEL.get(base, base)


def tokens(texte: str | None) -> frozenset[str]:
    """Ensemble des mots normalises."""
    return frozenset(normaliser(texte).split())


def tokens_distinctifs(nom: str | None) -> frozenset[str]:
    """Mots qui portent reellement l'identite du produit.

    « Exchange Server » -> {« exchange »}, pour retrouver l'avis CERT-FR
    intitule « Multiples vulnerabilites dans Microsoft Exchange ». Si le nom
    n'est fait que de mots generiques, on les conserve tous plutot que de
    renvoyer un ensemble vide (qui matcherait alors n'importe quoi).
    """
    tous = tokens(canoniser_produit(nom))
    distinctifs = frozenset(t for t in tous if t not in _BRUIT_PRODUIT)
    return distinctifs or tous


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Recouvrement de deux ensembles de mots, entre 0 et 1."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
