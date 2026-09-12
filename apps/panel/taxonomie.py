"""
Taxonomie fournie pour la declaration d'actifs (brief section 3, methode 1 :
"Declaratif manuel : taxonomie fournie (categorie -> editeur -> produit),
le client coche" — pas de saisie libre).

Catalogue de reference simple pour ce POC. A terme, remplacable par une
table administrable sans changer l'API du formulaire (meme structure
imbriquee categorie -> editeur -> [produits]).
"""

TAXONOMIE_TECHNIQUE = {
    "Pare-feu": {
        "Palo Alto Networks": ["PAN-OS"],
        "Fortinet": ["FortiOS"],
        "Cisco": ["ASA", "Firepower Threat Defense"],
        "Stormshield": ["Stormshield Network Security"],
    },
    "Système d'exploitation": {
        "Microsoft": ["Windows 11", "Windows Server 2022", "Windows Server 2025"],
        "Red Hat": ["Red Hat Enterprise Linux 9"],
        "Canonical": ["Ubuntu Server 24.04 LTS"],
        "Debian Project": ["Debian 13"],
    },
    "Langage / runtime": {
        "Python Software Foundation": ["Python"],
        "Oracle": ["Java (OpenJDK/Oracle JDK)"],
        "Node.js Foundation": ["Node.js"],
    },
    "Base de données": {
        "PostgreSQL Global Development Group": ["PostgreSQL"],
        "Oracle": ["MySQL", "Oracle Database"],
        "MongoDB Inc.": ["MongoDB"],
    },
    "Virtualisation / conteneurs": {
        "VMware": ["vSphere ESXi"],
        "Docker Inc.": ["Docker Engine"],
        "Proxmox Server Solutions": ["Proxmox VE"],
    },
    "Messagerie": {
        "Microsoft": ["Exchange Server", "Microsoft 365"],
        "Zimbra": ["Zimbra Collaboration Suite"],
    },
    "Applicatif web": {
        "GitLab Inc.": ["GitLab CE/EE"],
        "Atlassian": ["Confluence", "Jira"],
        "WordPress Foundation": ["WordPress"],
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
