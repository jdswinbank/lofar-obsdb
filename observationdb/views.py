from django.http import HttpResponse
from django.shortcuts import render_to_response
from observationdb.models import Survey, Field
import math

def surveys(request):
    surveys = Survey.objects.all()
    return render_to_response('surveys.html', {'survey_list': surveys})

def position_search(request, ra=0, dec=0):
    closest = sorted(Field.objects.all(), key=lambda field: field.distance_from(ra, dec))[0]
    return HttpResponse("%s at %f radians" % (closest.name, closest.distance_from(ra, dec)))
