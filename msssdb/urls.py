from django.conf.urls import patterns, include, url
from django.views.generic import ListView, DetailView
from django.contrib import admin

from observationdb.models import Survey

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
    url(r'^$',
        ListView.as_view(
            queryset=Survey.objects.all(),
            context_object_name='survey_list',
            template_name='survey_list.html'
        )
    ),
    url(r'^survey/(?P<pk>\d+)/$', 'observationdb.views.survey_summary'),

    url(r'^observation/(?P<pk>\d+)/$', 'observationdb.views.observation_detail'),

    url(r'^field/(?P<pk>\d+)/$', 'observationdb.views.field_detail'),
    url(r'^field/$', 'observationdb.views.field_list'),

    url(r'^position_search/$', 'observationdb.views.position_search'),



)
