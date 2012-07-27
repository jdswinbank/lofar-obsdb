from django import template
from ..models import FieldStatus

register = template.Library()

@register.filter
def status_icon(status):
    if status == FieldStatus.CALIBRATOR:
        return "icon-cog"
    elif status == FieldStatus.NOT_OBSERVED:
        return "icon-remove"
    elif status == FieldStatus.ARCHIVED:
        return "icon-hdd"
    elif status == FieldStatus.ON_CEP:
        return "icon-star"
    elif status == FieldStatus.PARTIAL:
        return "icon-star-empty"
    elif status == FieldStatus.UNKNOWN:
        return "icon-question-sign"
