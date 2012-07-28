from django import template
from ..models import DataStatus

register = template.Library()

@register.filter
def status_icon(status):
    if status == DataStatus.CALIBRATOR:
        return "icon-cog"
    elif status == DataStatus.NOT_OBSERVED:
        return "icon-remove"
    elif status == DataStatus.ARCHIVED:
        return "icon-folder-close"
    elif status == DataStatus.PARTIAL_ARCHIVED:
        return "icon-folder-open"
    elif status == DataStatus.ON_CEP:
        return "icon-star"
    elif status == DataStatus.PARTIAL_CEP:
        return "icon-star-empty"
    elif status == DataStatus.UNKNOWN:
        return "icon-question-sign"
