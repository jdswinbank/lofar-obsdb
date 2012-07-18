from django.db import models
from pyrap.measures import measures

EPOCH = "J2000"

class Survey(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('observationdb.views.survey_summary', [str(self.name)])

class Field(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True)
    ra = models.FloatField()
    dec = models.FloatField()
    survey = models.ForeignKey(Survey)
    calibrator = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('field_detail', [str(self.pk)])

    def distance_from(self, ra, dec):
        """
        Returns angular distance between self and ra, dec. All values are
        given and returned in radians.
        """
        dm = measures()
        return dm.separation(
            dm.direction(EPOCH, "%frad" % ra, "%frad" % dec),
            dm.direction(EPOCH, "%frad" % self.ra, "%frad" % self.dec)
        ).get_value("rad")

class Station(models.Model):
    name = models.CharField(max_length=10, unique=True)
    idnumber = models.IntegerField(unique=True)
    longitude = models.FloatField()
    latitude = models.FloatField()
    height = models.FloatField()
    location = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        return self.name

class Observation(models.Model):
    ANTENNASET_CHOICES = (
        ('HBA_DUAL', 'HBA_DUAL'),
        ('HBA_DUAL_INNER', 'HBA_DUAL_INNER'),
        ('HBA_JOINED', 'HBA_JOINED'),
        ('HBA_ONE', 'HBA_ONE'),
        ('HBA_ZERO', 'HBA_ZERO'),
        ('HBA_ZERO_INNER', 'HBA_ZERO_INNER'),
        ('LBA_INNER', 'LBA_INNER'),
        ('LBA_OUTER', 'LBA_OUTER'),
        ('LBA_X', 'LBA_X'),
        ('LBA_Y', 'LBA_Y')
    )
    CLOCK_CHOICES = (
        (160, "160 MHz"),
        (200, "200 MHz")
    )

    obsid = models.CharField(max_length=10, primary_key=True)
    stations = models.ManyToManyField(Station)
    antennaset = models.CharField(max_length=15, choices=ANTENNASET_CHOICES)
    start_time = models.DateTimeField()
    duration = models.IntegerField() # Always an integral number of seconds?
    clock = models.IntegerField(choices=CLOCK_CHOICES)
    parset = models.TextField()

    def __unicode__(self):
        return self.obsid

    @models.permalink
    def get_absolute_url(self):
        return ('observation_detail', [str(self.obsid)])

    class Meta:
        ordering = ['start_time']

class Subband(models.Model):
    number = models.IntegerField(unique=True)

    def __unicode__(self):
        return str(self.number)

    class Meta:
        ordering = ['number']

class Beam(models.Model):
    observation = models.ForeignKey(Observation)
    beam = models.IntegerField()
    field = models.ForeignKey(Field)
    subbands = models.ManyToManyField(Subband)

    def __unicode__(self):
        return self.observation.obsid + " beam " + str(self.beam)

    class Meta:
        ordering = ['observation__start_time']
