import math

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Min, Max, Count

from observationdb.models import Survey, Field, Observation
from observationdb.forms import FieldFilterForm

def intro(request):
    return render_to_response(
        'base.html',
        {
            'n_surveys': Survey.objects.count(),
            'survey_list': Survey.objects.all(),
            'n_fields': Field.objects.count(),
            'n_targets': Field.objects.filter(calibrator=False).count(),
            'n_calibrators': Field.objects.filter(calibrator=True).count(),
            'n_observations': Observation.objects.count()
            }
    )

def survey_summary(request, pk):
    s = Survey.objects.get(pk=pk)
    n_beams = s.field_set.aggregate(Count('beam'))['beam__count']
    start_time = s.field_set.aggregate(Min('beam__observation__start_time')).values()[0]
    stop_time = s.field_set.aggregate(Max('beam__observation__start_time')).values()[0]

    return render_to_response(
        'survey_detail.html',
        {'survey': s, 'n_beams': n_beams, 'start_time': start_time, 'stop_time': stop_time}
    )

def observation_detail(request, pk):
    o = Observation.objects.get(pk=pk)
    return render_to_response('observation_detail.html', {'observation': o})

def field_detail(request, pk):
    f = Field.objects.get(pk=pk)
    return render_to_response('field_detail.html', {'field': f})

def field_list(request):
    fields = Field.objects.all()
    if request.method == 'POST' and not 'clear' in request.POST:
        form = FieldFilterForm(request.POST)
        if form.is_valid():
            ra = form.cleaned_data['ra']
            dec = form.cleaned_data['dec']
            radius = form.cleaned_data['radius']
            if not None in (ra, dec, radius):
                # Fudge factor to account for floating point rouding errors:
                # dec of 90 with 90 degree search doesn't quite hit dec of 0!
                fields = filter(lambda x: x.distance_from(math.radians(ra), math.radians(dec)) <= math.radians(radius) + 1e-5, fields)
    else:
        form = FieldFilterForm()

    return render_to_response(
        'field_list.html',
        {'field_list': fields, 'form': form},
        context_instance=RequestContext(request)
    )
