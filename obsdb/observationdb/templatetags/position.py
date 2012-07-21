from django import template
from django.utils.safestring import mark_safe

import math
from ..utils import radians_to_hms
from ..utils import radians_to_dms

register = template.Library()

@register.filter
def format_angle(value, format_type):
    if format_type == "time":
        h, m, s = radians_to_hms(float(value))
        result = "%d<sup>h</sup> %d<sup>m</sup> %.1f<sup>s</sup>" % (h, m, s)
    if format_type == "dms":
        sign, d, m, s = radians_to_dms(float(value))
        result = "%s%d&deg; %d&prime; %.1f&Prime;" % (sign, d, m, s)
    return mark_safe(result)

@register.filter
def to_degrees(value):
    return math.degrees(value)
