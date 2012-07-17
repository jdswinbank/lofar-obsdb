from django import template
from pyrap.quanta import quantity
import math

register = template.Library()

@register.filter
def format_angle(value, format_type):
    q = quantity("%frad" % value)
    return q.formatted(str(format_type))

@register.filter
def to_degrees(value):
    return math.degrees(value)
