import math

from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Min, Max, Count, Q
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models.query import QuerySet

from .models import Survey, Field, Observation, Constants, FieldStatus
from .forms import LookupForm, FieldFilterForm

from ..settings import PAGE_SIZE

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
            'n_archived': Observation.objects.filter(archived=Constants.TRUE).count()
        },
        context_instance=RequestContext(request)
    )

def survey_summary(request, pk):
    try:
        s = Survey.objects.get(pk=pk)
    except ObjectDoesNotExist:
        raise Http404

    n_targets = s.field_set.filter(calibrator=False).count()
    n_cals = s.field_set.filter(calibrator=True).count()
    start_time = s.field_set.aggregate(Min('beam__observation__start_time')).values()[0]
    stop_time = s.field_set.aggregate(Max('beam__observation__start_time')).values()[0]
    n_done = s.field_set.filter(calibrator=False, done=True).count()
    if n_targets > 0:
        percentage = 100 * float(n_done)/n_targets
    else:
        percentage = 0

    field_list = []
    for f in s.field_set.filter(calibrator=False):
        if f.beam_set.count() == 0:
            # Not observed
            colour = "o"
        elif f.archived == Constants.TRUE:
            # Data has been archived
            colour = "p"
        elif f.on_cep == Constants.TRUE:
            # Data available on CEP
            colour = "g"
        elif f.on_cep == Constants.PARTIAL or f.archived == Constants.PARTIAL:
            # Partially observed
            colour = "b"
        else:
            # Data missing
            colour = "r"

        field_list.append((f.ra, f.dec, colour))

    return render_to_response(
        'survey_detail.html',
        {
            'survey': s,
            'field_list': field_list,
            'field_size': s.field_size,
            'n_targets': n_targets,
            'n_done': n_done,
            'percentage': percentage,
            'start_time': start_time,
            'stop_time': stop_time,
            'n_cals': n_cals
        }
    )

def field_list(request):
    fields = Field.objects.all()
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
                pass

            # Filter by survey
            if form.cleaned_data['survey']:
                fields = fields.filter(survey_id=form.cleaned_data['survey'])

            # Filter by status
            fields = fields.annotate(num_beams=Count('beam'))
            if form.cleaned_data['status'] and form.cleaned_data['status'] != "None":
                status = form.cleaned_data['status']
                if status == FieldStatus.CALIBRATOR:
                    fields = fields.filter(calibrator=True)
                elif status == FieldStatus.NOT_OBSERVED:
                    fields = fields.filter(num_beams=0)
                elif status == FieldStatus.ARCHIVED:
                    fields = fields.filter(archived=Constants.TRUE)
                elif status == FieldStatus.ON_CEP:
                    fields = fields.filter(on_cep=Constants.TRUE)
                elif status == FieldStatus.PARTIAL:
                    fields = fields.filter(Q(on_cep=Constants.PARTIAL) | Q(archived=Constants.PARTIAL))
                else:
                    fields = fields.filter(calibrator=False, archived=Constants.FALSE, on_cep=Constants.FALSE).exclude(num_beams=0)

            # Prepare for display
            if form.cleaned_data['sort_by'] in ("name", "ra", "dec"):
                fields = fields.order_by(form.cleaned_data['sort_by'])
            elif form.cleaned_data['sort_by'] == "obs":
                fields = fields.order_by('-num_beams')
            elif form.cleaned_data['sort_by'] == "dist":
                fields = sorted(fields, key=lambda x: x.distance)
            if form.cleaned_data['reverse']:
                # The semantics of reverse() are different for querysets and
                # normal Python iterators.
                if isinstance(fields, QuerySet):
                    fields = fields.reverse()
                else:
                    fields.reverse()

    else:
        form = FieldFilterForm()

    queries = request.GET.copy()
    if queries.has_key('page'):
        page = int(queries['page'])
        del queries['page']
    else:
        page = 1

    paginator = Paginator(fields, PAGE_SIZE)
    field_list = paginator.page(page)

    return render_to_response(
        'field_list.html',
        {'field_list': field_list, 'form': form, 'queries': queries},
        context_instance=RequestContext(request)
    )

def field_detail(request, pk):
    field = Field.objects.get(pk=pk)
    paginator = Paginator(field.beam_set.all(), PAGE_SIZE)
    page = request.GET.get('page')
    try:
        beam_set = paginator.page(page)
    except PageNotAnInteger:
        beam_set = paginator.page(1)
    except EmptyPage:
        beam_set = paginator.page(paginator.num_pages)

    return render_to_response(
        'field_detail.html',
        {'field': field, 'beam_set': beam_set},
        context_instance=RequestContext(request)
    )
