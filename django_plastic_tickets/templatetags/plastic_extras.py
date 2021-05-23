from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext

register = template.Library()


@register.filter
def ticketbadge(value) -> str:
    if value == "UN":
        flavor, text = "warning", gettext("NEW")
    elif value == "PR":
        flavor, text = "info", gettext("IN PROGRESS")
    elif value == "RE":
        flavor, text = "danger", gettext("REJECTED")
    elif value == "DO":
        flavor, text = "success", gettext("DONE")
    return mark_safe(
        f'<span class="badge badge-pill badge-{flavor}">{text}</span>')
