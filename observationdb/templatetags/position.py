from django import template
from pyrap.quanta import quantity

register = template.Library()

@register.filter
def format_angle(value, format_type):
    q = quantity("%frad" % value)
    return q.formatted(str(format_type))
