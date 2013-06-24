from django.conf.urls import patterns, include, url
from django.views.generic import DetailView

from .views import IntroView
from .views import SurveyDetailView
from .views import FieldDetailView
from .views import FieldListView
from .views import ObservationDetailView
from .views import ObservationListView

from ..settings import PAGE_SIZE

urlpatterns = patterns('obsdb.observationdb.views',
    # Intro & surveys
    url(r'^$', IntroView.as_view(), name="introduction"),
    url(r'^survey/(?P<pk>.+)/$', SurveyDetailView.as_view(), name="survey_detail"),

    # Fields
    url(r'^field/(?P<pk>\d+)/$', FieldDetailView.as_view(), name="field_detail"),
    url(r'^field/$', FieldListView.as_view(), name="field_list"),

    # Observations
    url(r'^observation/(?P<pk>L\d+)/$', ObservationDetailView.as_view(), name="observation_detail"),
    url(r'^observation/$', ObservationListView.as_view(), name="obs_list"),
)
