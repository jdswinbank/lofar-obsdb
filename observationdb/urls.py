from django.conf.urls import patterns, include, url
from django.views.generic import ListView, DetailView
from django.views.generic.simple import redirect_to

from .models import Survey, Observation, Field

urlpatterns = patterns('',
    url(r'^$', 'observationdb.views.intro'),

    url(r'^survey/(?P<pk>.+)/$', 'observationdb.views.survey_summary'),

    url(r'^observation/$', redirect_to, {'url': '/observation/page1'}),
    url(r'^observation/(?P<pk>L\d+)/$',
        DetailView.as_view(
            model=Observation,
            template_name='observation_detail.html'
        ),
        name="observation_detail"
    ),
    url(r'^observation/page(?P<page>\d+)/$',
        ListView.as_view(
            queryset=Observation.objects.all(),
            context_object_name='obs_list',
            template_name='observation_list.html',
            paginate_by=200,
        ),
        name="obs_list"
    ),

    url(r'^field/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Field,
            template_name='field_detail.html'
        ),
        name="field_detail"
    ),
    url(r'^field/$', 'observationdb.views.field_list'),
)
