"""Small helpers for the dashboard templates."""
from django import template

register = template.Library()


@register.filter
def in_group(field, names):
    """
    True when a bound field's name is in a space-separated list.

    Used to lay form fields out in sections. Django's built-in ``in`` does a
    substring test on a string, which quietly matches partial names — this
    compares whole names only.
    """
    return field.name in names.split()
