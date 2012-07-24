from django.contrib import admin
from .models import Survey
from .models import Field
from .models import Station
from .models import Observation
from .models import Beam
from .models import SubbandData
from .models import ArchiveSite

admin.site.register(Survey)
admin.site.register(Field)
admin.site.register(Station)
admin.site.register(Observation)
admin.site.register(Beam)
admin.site.register(SubbandData)
admin.site.register(ArchiveSite)
