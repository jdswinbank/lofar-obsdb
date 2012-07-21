import math

from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Min, Max, Count
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator

from observationdb.models import Survey, Field, Observation
from observationdb.forms import LookupForm, FieldFilterForm

def intro(request):
    if request.method == 'POST':
        form = LookupForm(request.POST)
        if form.is_valid():
            try:
                if "field" in request.POST:
                    field = Field.objects.get(name=form.cleaned_data['target'])
                    return HttpResponseRedirect(reverse('field_detail', args=(field.id,)))
                elif "obs" in request.POST:
                    return HttpResponseRedirect(reverse('observation_detail', args=(form.cleaned_data['target'],)))
            except:
                raise Http404

    return render_to_response(
        'base.html',
        {
            'n_surveys': Survey.objects.count(),
            'survey_list': Survey.objects.all(),
            'n_fields': Field.objects.count(),
            'n_targets': Field.objects.filter(calibrator=False).count(),
            'n_calibrators': Field.objects.filter(calibrator=True).count(),
            'n_observations': Observation.objects.count(),
        },
        context_instance=RequestContext(request)
    )

def survey_summary(request, pk):
    try:
        s = Survey.objects.get(pk=pk)
    except ObjectDoesNotExist:
        raise Http404
    n_beams = s.field_set.aggregate(Count('beam'))['beam__count']
    n_observed = s.field_set.annotate(num_beams=Count('beam')).filter(num_beams__gt=0).count()
    if s.field_set.count() > 0:
        percentage = 100*float(n_observed)/s.field_set.count()

        # Assuming data is on a regular grid, we set the size of the grid
        # cells equal to whichever is larger of the difference between the
        # points in RA and dec space.
        decs = s.field_set.values_list('dec').distinct().order_by('dec')[0:2]
        ras = s.field_set.values_list('ra').distinct().order_by('ra')[0:2]
        field_size = math.degrees(max(decs[1][0]-decs[0][0], ras[1][0]-ras[0][0]))/2
    else:
        percentage = 0
        field_size = 0
    start_time = s.field_set.aggregate(Min('beam__observation__start_time')).values()[0]
    stop_time = s.field_set.aggregate(Max('beam__observation__start_time')).values()[0]
    field_list = [
        (f.ra, f.dec, "g" if f.beam_set.count() else "r")
        for f in s.field_set.filter(calibrator=False)
    ]

    return render_to_response(
        'survey_detail.html',
        {
            'survey': s,
            'field_list': field_list,
            'field_size': field_size,
            'n_beams': n_beams,
            'n_observed': n_observed,
            'percentage': percentage,
            'start_time': start_time,
            'stop_time': stop_time
        }
    )

def field_list(request):
    if request.method == 'GET' and not 'clear' in request.GET:
        form = FieldFilterForm(request.GET)
        if form.is_valid():
            # Filter by position
            try:
                ra = math.radians(form.cleaned_data['ra'])
                dec = math.radians(form.cleaned_data['dec'])
                radius = math.radians(form.cleaned_data['radius'])
                # Fudge factor of 1e-5 to avoid rounding errors.
                fields = Field.objects.near_position(ra, dec, radius+1e-5)
            except TypeError:
                # One of the above wasn't specified -- skip this filter.
                fields = Field.objects.all()

            # Filter by survey
            if form.cleaned_data['survey']:
                fields = fields.filter(survey_id=form.cleaned_data['survey'])

            # Prepare for display
            fields = fields.annotate(num_beams=Count('beam'))
            if form.cleaned_data['sort_by'] in ("name", "ra", "dec"):
                fields = fields.order_by(form.cleaned_data['sort_by'])
            elif form.cleaned_data['sort_by'] == "obs":
                fields = fields.order_by('-num_beams')
            if form.cleaned_data['reverse']:
                fields = fields.reverse()

    else:
        fields = Field.objects.all()
        form = FieldFilterForm()

    queries = request.GET.copy()
    if queries.has_key('page'):
        page = int(queries['page'])
        del queries['page']
    else:
        page = 1

    paginator = Paginator(fields, 100)
    field_list = paginator.page(page)

    return render_to_response(
        'field_list.html',
        {'field_list': field_list, 'form': form, 'queries': queries},
        context_instance=RequestContext(request)
    )
