from django.conf.urls import patterns, include, url
from django.views.generic import ListView, TemplateView
from django.views.generic.simple import redirect_to
from django.contrib import admin

from observationdb.models import Survey, Observation

admin.autodiscover()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'msssdb.views.home', name='home'),
    # url(r'^msssdb/', include('msssdb.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),


#    url(r'^surveys/$', 'observationdb.views.surveys'),
    url(r'^$', 'observationdb.views.intro'),


    url(r'^survey/$',
        ListView.as_view(
            queryset=Survey.objects.all(),
            context_object_name='survey_list',
            template_name='survey_list.html'
        )
    ),
    url(r'^survey/(?P<pk>\d+)/$', 'observationdb.views.survey_summary'),

    url(r'^observation/$', redirect_to, {'url': '/observation/page1'}),
    url(r'^observation/page(?P<page>[0-9]+)/$',
        ListView.as_view(
            queryset=Observation.objects.all(),
            context_object_name='obs_list',
            template_name='observation_list.html',
            paginate_by=200,
        ),
        name="obs_list"
    ),
    url(r'^observation/(?P<pk>\d+)/$', 'observationdb.views.observation_detail'),

    url(r'^field/(?P<pk>\d+)/$', 'observationdb.views.field_detail'),
    url(r'^field/$', 'observationdb.views.field_list'),
)
