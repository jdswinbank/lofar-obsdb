from django.conf.urls import patterns, include, url
from django.views.generic import ListView, DetailView
from django.views.generic.simple import redirect_to

from .models import Survey, Observation, Field

urlpatterns = patterns('obsdb.observationdb.views',
    # Intro & surveys
    url(r'^$', 'intro'),
    url(r'^survey/(?P<pk>.+)/$', 'survey_summary'),

    # Fields
    url(r'^field/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Field,
            template_name='field_detail.html'
        ),
        name="field_detail"
    ),
    url(r'^field/$', 'field_list'),

    # Observations
    url(r'^observation/(?P<pk>L\d+)/$',
        DetailView.as_view(
            model=Observation,
            template_name='observation_detail.html'
        ),
        name="observation_detail"
    ),
    url(r'^observation/$',
        ListView.as_view(
            queryset=Observation.objects.all(),
            context_object_name='obs_list',
            template_name='observation_list.html',
            paginate_by=100,
        ),
        name="obs_list"
    ),
)
