from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from observationdb.models import Survey, Field
from observationdb.forms import PositionSearchForm

def surveys(request):
    surveys = Survey.objects.all()
    return render_to_response('surveys.html', {'survey_list': surveys})

def position_search(request):
    if request.method == 'POST':
        form = PositionSearchForm(request.POST)
        if form.is_valid():
            ra = form.cleaned_data['ra']
            dec = form.cleaned_data['dec']
            closest = sorted(Field.objects.all(), key=lambda field: field.distance_from(ra, dec))[0]
            return HttpResponse("%s at %f radians" % (closest.name, closest.distance_from(ra, dec)))
    else:
        form = PositionSearchForm()

    return render_to_response('position_search.html', {'form': form}, context_instance=RequestContext(request))
