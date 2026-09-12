from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Lookup par cle dans un dict passe au contexte (les templates Django
    ne supportent pas dict[key] avec une variable)."""
    if mapping is None:
        return None
    return mapping.get(key)
