from django.contrib import admin
from .models import Survey
from .models import Field
from .models import Station
from .models import Observation
from .models import Beam

admin.site.register(Survey)
admin.site.register(Field)
admin.site.register(Station)
admin.site.register(Observation)
admin.site.register(Beam)
