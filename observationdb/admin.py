from django.contrib import admin
from observationdb.models import Survey
from observationdb.models import Field
from observationdb.models import Station
from observationdb.models import Observation
from observationdb.models import Beam

admin.site.register(Survey)
admin.site.register(Field)
admin.site.register(Station)
admin.site.register(Observation)
admin.site.register(Beam)
