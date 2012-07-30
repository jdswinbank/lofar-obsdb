import math

SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 60**2
SECONDS_IN_DAY = 24 * SECONDS_IN_HOUR
RADIANS_IN_CIRCLE = 2 * math.pi

ASEC_IN_AMIN = 60
ASEC_IN_DEGREE = 60**2

def radians_to_hms(rad):
    rad = rad % (RADIANS_IN_CIRCLE)
    seconds = SECONDS_IN_DAY * rad / RADIANS_IN_CIRCLE
    hours, seconds = divmod(seconds, SECONDS_IN_HOUR)
    minutes, seconds = divmod(seconds, SECONDS_IN_MINUTE)
    return hours, minutes, seconds

def radians_to_dms(rad):
    sign = "+" if rad >= 0 else "-"
    rad = abs(rad)
    seconds = math.degrees(rad) * ASEC_IN_DEGREE
    degrees, seconds = divmod(seconds, ASEC_IN_DEGREE)
    minutes, seconds = divmod(seconds, ASEC_IN_AMIN)
    return sign, degrees, minutes, seconds

def hms_to_radians(h, m, s):
    seconds = SECONDS_IN_HOUR * h +   \
              SECONDS_IN_MINUTE * m + \
              s
    return RADIANS_IN_CIRCLE * seconds / SECONDS_IN_DAY

def dms_to_radians(d, m ,s):
    sign = 1 if d >= 0 else -1
    d = abs(d)
    seconds = ASEC_IN_DEGREE * d + \
              ASEC_IN_AMIN * m +   \
              s
    return sign * math.radians(seconds / ASEC_IN_DEGREE)
