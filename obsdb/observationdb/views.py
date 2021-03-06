import math
from random import choice

from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.db.models import Min, Max, Count, Q
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models.query import QuerySet
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.utils.safestring import mark_safe

from .models import Survey, Field, Observation, Constants, DataStatus
from .forms import LookupForm, FieldFilterForm

from ..settings import PAGE_SIZE
from ..settings import SPLASH_IMAGES

class IntroView(TemplateView, ProcessFormView, FormMixin):
    form_class = LookupForm
    template_name = 'intro.html'

    def form_valid(self, form):
        try:
            if "field" in self.request.POST:
                if form.cleaned_data['survey']:
                    fields = Field.objects.filter(survey=form.cleaned_data['survey'])
                else:
                    fields = Field.objects.all()
                field = fields.filter(name=form.cleaned_data['target'])[0]
                return HttpResponseRedirect(reverse('field_detail', args=(field.id,)))
            elif "obs" in self.request.POST:
                return HttpResponseRedirect(reverse('observation_detail', args=(form.cleaned_data['target'],)))
        except:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(IntroView, self).get_context_data(**kwargs)
        image_url, image_caption = choice(SPLASH_IMAGES)
        context.update({
            'n_surveys': Survey.objects.count(),
            'survey_list': Survey.objects.all(),
            'n_fields': Field.objects.count(),
            'n_targets': Field.objects.filter(calibrator=False).count(),
            'n_calibrators': Field.objects.filter(calibrator=True).count(),
            'n_observations': Observation.objects.count(),
            'n_archived': Observation.objects.filter(archived=Constants.TRUE).count(),
            'image_url': image_url,
            'image_caption': mark_safe(image_caption)
        })
        return context


class SurveyDetailView(DetailView):
    model = Survey
    template_name = 'survey_detail.html'
    context_object_name = "survey"

    def _generate_field_list(self):
        field_list = []
        counts = {}
        non_calibrators = self.object.field_set.filter(calibrator=False).annotate(n_beams=Count('beam'))

        not_obs = non_calibrators.filter(n_beams=0)
        field_list.extend([ra, dec, 'o'] for ra, dec in not_obs.values_list("ra", "dec"))
        counts["not_observed"] = not_obs.count()

        on_cep = non_calibrators.filter(on_cep=Constants.TRUE)
        field_list.extend([ra, dec, 'p'] for ra, dec in on_cep.values_list("ra", "dec"))
        counts["on_cep"] = on_cep.count()

        archived = non_calibrators.filter(archived=Constants.TRUE).exclude(on_cep=Constants.TRUE)
        field_list.extend([ra, dec, 'g'] for ra, dec in archived.values_list("ra", "dec"))
        counts["archived"] = archived.count()

        partial = non_calibrators.filter(Q(archived=Constants.PARTIAL) | Q(on_cep=Constants.PARTIAL)).exclude(on_cep=Constants.TRUE).exclude(archived=Constants.TRUE)
        field_list.extend([ra, dec, 'b'] for ra, dec in partial.values_list("ra", "dec"))
        counts["partial"] = partial.count()

        # This includes data which both couldn't be located at all and also
        # data which is accounted for but has been marked as invalid by the
        # observers.
        missing = non_calibrators.filter(n_beams__gt=0).filter(archived=Constants.FALSE, on_cep=Constants.FALSE).prefetch_related('beam_set', 'beam_set__observation')
        field_list.extend([ra, dec, 'r'] for ra, dec in missing.values_list("ra", "dec"))
        counts["missing"] = missing.count()

        return field_list, counts

    def get_context_data(self, **kwargs):
        context = super(SurveyDetailView, self).get_context_data(**kwargs)
        s = self.object
        n_targets = s.field_set.filter(calibrator=False).count()
        n_done = s.field_set.filter(calibrator=False, done=True).count()
        field_list, counts = self._generate_field_list()
        if n_targets > 0:
            percentages = { key : 100 * float(value)/n_targets for key, value in counts.iteritems() }
            percentages["done"] = 100 * float(n_done)/n_targets
        else:
            percentages = { key : 0 for key, value in counts }
            percentages["done"] = 0

        context.update({
            "n_targets": n_targets, "n_done": n_done,
            "n_cals": s.field_set.filter(calibrator=True).count(),
            "start_time": s.field_set.aggregate(Min('beam__observation__start_time')).values()[0],
            "stop_time": s.field_set.aggregate(Max('beam__observation__start_time')).values()[0],
            "percentages": percentages,
            "field_list": field_list,
            'field_size': s.field_size,
        })
        return context


class FieldDetailView(DetailView):
    model = Field
    template_name = "field_detail.html"
    context_object_name = "field"

    def get_context_data(self, **kwargs):
        context = super(FieldDetailView, self).get_context_data(**kwargs)
        paginator = Paginator(self.object.beam_set.all(), PAGE_SIZE)
        page = self.request.GET.get('page')
        try:
            beam_set = paginator.page(page)
        except PageNotAnInteger:
            beam_set = paginator.page(1)
        except EmptyPage:
            beam_set = paginator.page(paginator.num_pages)
        context['beam_set'] = beam_set
        return context


class FieldListView(ListView, FormMixin):
    model = Field
    form_class = FieldFilterForm
    template_name = "field_list.html"
    paginate_by = 100
    context_object_name = "field_list"

    def get_form_kwargs(self):
        kwargs = {'initial': self.get_initial()}
        kwargs.update({'data': self.request.GET})
        return kwargs

    def get(self, request, *args, **kwargs):
        if "clear" in request.GET:
            return HttpResponseRedirect(reverse('field_list'))
        else:
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

    def form_valid(self, form):
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

        # Filter by status
        fields = fields.annotate(num_beams=Count('beam'))
        if form.cleaned_data['status'] and form.cleaned_data['status'] != "None":
            status = form.cleaned_data['status']
            if status == DataStatus.CALIBRATOR:
                fields = fields.filter(calibrator=True)
            elif status == DataStatus.NOT_OBSERVED:
                fields = fields.filter(num_beams=0)
            elif status == DataStatus.ARCHIVED:
                fields = fields.filter(archived=Constants.TRUE)
            elif status == DataStatus.ON_CEP:
                fields = fields.filter(on_cep=Constants.TRUE)
            elif status == DataStatus.PARTIAL_ARCHIVED:
                fields = fields.filter(archived=Constants.PARTIAL)
            elif status == DataStatus.PARTIAL_CEP:
                fields = fields.filter(on_cep=Constants.PARTIAL)
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

        self.object_list = fields
        return self.render_to_response(self.get_context_data(form=form, object_list=self.object_list))

    def form_invalid(self, form):
        self.object_list = self.model.objects.all()
        return self.render_to_response(self.get_context_data(form=form, object_list=self.object_list))

    def get_context_data(self, **kwargs):
        context = super(FieldListView, self).get_context_data(**kwargs)
        queries = self.request.GET.copy()
        if queries.has_key('page'):
            del(queries['page'])
        context['queries'] = queries
        return context


class ObservationDetailView(DetailView):
    model = Observation
    template_name = 'observation_detail.html'


class ObservationListView(ListView):
    queryset = Observation.objects.all()
    context_object_name = 'obs_list'
    template_name = 'observation_list.html'
    paginate_by = PAGE_SIZE

    def get_context_data(self, **kwargs):
        context = super(ObservationListView, self).get_context_data(**kwargs)
        good_observations = Observation.objects.filter(invalid=False)
        context.update({
            "n_archived": good_observations.filter(archived=Constants.TRUE).count(),
            "n_part_archived": good_observations.filter(archived=Constants.PARTIAL).count(),
            "n_on_cep": good_observations.filter(on_cep=Constants.TRUE).count(),
            "n_part_on_cep": good_observations.filter(on_cep=Constants.PARTIAL).count(),
            "n_unknown": good_observations.filter(on_cep=Constants.FALSE, archived=Constants.FALSE).count(),
            "n_invalid": Observation.objects.filter(invalid=True).count()
        })
        return context
