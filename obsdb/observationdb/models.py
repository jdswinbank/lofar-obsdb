from django.db import models
from django.utils.datastructures import SortedDict

from math import sin, cos, acos

EPOCH = "J2000"

# These are the states which Fields, Observations and Beams can have to
# reflect where their data is available.
ARCHIVE_CHOICES = (
    ("true", "Archived"),
    ("partial", "Partially archived"),
    ("false", "Not archived")
)
ON_CEP_CHOICES = (
    ("true", "Available on CEP"),
    ("partial", "Partially available on CEP"),
    ("false", "Not available on CEP")
)
MAX_CHOICE_LENGTH=len("partial")

class ArchiveSite(models.Model):
    name = models.CharField(max_length=20, primary_key=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Station(models.Model):
    idnumber = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=100, blank=True)
    longitude = models.FloatField()
    latitude = models.FloatField()
    altitude = models.FloatField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Subband(models.Model):
    number = models.IntegerField(unique=True, primary_key=True)

    def __unicode__(self):
        return str(self.number)

    class Meta:
        ordering = ['number']


class Survey(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    description = models.TextField(blank=True)
    beams_per_field = models.IntegerField(default=9) # 9 for MSSS_LBA
    field_size = models.FloatField() # 2.885 for MSSS_LBA, 1.21 for MSSS_HBA

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('obsdb.observationdb.views.survey_summary', [str(self.name)])


class FieldManager(models.Manager):
    def near_position(self, ra, dec, radius):
        """
        Return a QuerySet containing those objects within radius of ra, dec.
        All arguments should be given in radians.

        The returned fields will have an extra attribute, distance, giving the
        angular separation in radians from the ra, dec supplied.
        """
        return super(FieldManager, self).get_query_set().filter(
            dec__gte=dec-radius, dec__lte=dec+radius
        ).extra(
            select=SortedDict([('distance', 'SELECT ACOS(SIN(dec)*SIN(%s) + COS(dec)*COS(%s)*COS(ra-%s))')]),
            select_params=(dec, dec, ra),
            where=['ACOS(SIN(dec)*SIN(%s) + COS(dec)*COS(%s)*COS(ra-%s)) <= %s'],
            params=[dec, dec, ra, radius]
        )


class Field(models.Model):
    objects = FieldManager()
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True)
    ra = models.FloatField()
    dec = models.FloatField()
    survey = models.ForeignKey(Survey)
    calibrator = models.BooleanField(default=False)
    archived = models.CharField(
        choices=ARCHIVE_CHOICES, max_length=MAX_CHOICE_LENGTH,
        default="false", editable=False
    )
    on_cep = models.CharField(
        choices=ON_CEP_CHOICES, max_length=MAX_CHOICE_LENGTH,
        default="false", editable=False
    )
    done = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def _update_status(self):
        beams_per_field = self.survey.beams_per_field

        if self.beam_set.filter(archived="true").count() >= beams_per_field:
            self.archived = "true"
        elif self.beam_set.filter(models.Q(archived="true") | models.Q(archived="partial")).count() > 0:
            self.archived = "partial"
        else:
            self.archived = "false"

        if self.beam_set.filter(on_cep="true").count() >= beams_per_field:
            self.on_cep = "true"
        elif self.beam_set.filter(models.Q(on_cep="true") | models.Q(on_cep="partial")).count() > 0:
            self.on_cep = "partial"
        else:
            self.on_cep = "false"

        if self.on_cep == "true" or self.archived == "true":
            self.done = True

        self.save()

    @models.permalink
    def get_absolute_url(self):
        return ('field_detail', [str(self.pk)])

    def distance_from(self, ra, dec):
        """
        Returns angular distance between self and ra, dec. All values are
        given and returned in radians.
        """
        return acos(sin(dec)*sin(self.dec) + cos(dec)*cos(self.dec)*cos(ra-self.ra))

    class Meta:
        ordering = ['name']


class Observation(models.Model):
    ANTENNASET_CHOICES = (
        ("HBA_DUAL", "HBA_DUAL"),
        ("HBA_DUAL_INNER", "HBA_DUAL_INNER"),
        ("HBA_JOINED", "HBA_JOINED"),
        ("HBA_ONE", "HBA_ONE"),
        ("HBA_ZERO", "HBA_ZERO"),
        ("HBA_ZERO_INNER", "HBA_ZERO_INNER"),
        ("LBA_INNER", "LBA_INNER"),
        ("LBA_OUTER", "LBA_OUTER"),
        ("LBA_X", "LBA_X"),
        ("LBA_Y", "LBA_Y")
    )
    CLOCK_CHOICES = (
        (160, "160 MHz"),
        (200, "200 MHz")
    )
    FILTER_CHOICES = (
        ("HBA_110_190", "110-190 MHz"),
        ("HBA_170_230", "170-230 MHz"),
        ("HBA_210_250", "210-250 MHz"),
        ("LBA_10_70", "10-70 MHz"),
        ("LBA_10_90", "10-90 MHz"),
        ("LBA_30_70", "30-70 MHz"),
        ("LBA_30_90", "30-90 MHz")
    )

    obsid = models.CharField(max_length=10, primary_key=True)
    stations = models.ManyToManyField(Station)
    antennaset = models.CharField(max_length=15, choices=ANTENNASET_CHOICES)
    start_time = models.DateTimeField()
    duration = models.IntegerField()
    clock = models.IntegerField(choices=CLOCK_CHOICES)
    filter = models.CharField(max_length=15, choices=FILTER_CHOICES)
    parset = models.TextField()
    archived = models.CharField(
        choices=ARCHIVE_CHOICES, max_length=MAX_CHOICE_LENGTH,
        default="false", editable=False
    )
    on_cep = models.CharField(
        choices=ON_CEP_CHOICES, max_length=MAX_CHOICE_LENGTH,
        default="false", editable=False
    )
    invalid = models.BooleanField(default=False) # For use by humans

    def __unicode__(self):
        return self.obsid

    def _update_status(self):
        n_beams = self.beam_set.count()

        if self.beam_set.filter(archived="true").count() == n_beams:
            self.archived = "true"
        elif self.beam_set.filter(models.Q(archived="true") | models.Q(archived="partial")).count() > 0:
            self.archived = "partial"
        else:
            self.archived = "false"

        if self.beam_set.filter(on_cep="true").count() == n_beams:
            self.on_cep = "true"
        elif self.beam_set.filter(models.Q(on_cep="true") | models.Q(on_cep="partial")).count() > 0:
            self.on_cep = "partial"
        else:
            self.on_cep = "false"

        self.save()

    @models.permalink
    def get_absolute_url(self):
        return ('observation_detail', [str(self.obsid)])

    class Meta:
        ordering = ['start_time']


class Beam(models.Model):
    observation = models.ForeignKey(Observation)
    beam = models.IntegerField()
    field = models.ForeignKey(Field)
    subbands = models.ManyToManyField(Subband)
    archived = models.CharField(choices=ARCHIVE_CHOICES, max_length=MAX_CHOICE_LENGTH, default="false", editable=False)
    on_cep = models.CharField(choices=ON_CEP_CHOICES, max_length=MAX_CHOICE_LENGTH, default="false", editable=False)
    invalid = models.BooleanField(default=False) # For use by humans

    def save(self, *args, **kwargs):
        # Augment save to mark our Observation & Field as archived if all of its subbands are
        # now archived.
        super(Beam, self).save(*args, **kwargs)
        self.observation._update_status()
        self.field._update_status()

    def _update_status(self):
        n_sbs = self.subbands.count()

        # If all our subbands are archived, we are archived.
        n_archived = self.subbanddata_set.exclude(archive=None).count()
        if n_archived == n_sbs:
            self.archived = "true"
        elif n_archived > 0:
            self.archived = "partial"
        else:
            self.archived = "false"

        # If all our subbands are on CEP, we are on CEP.
        n_on_cep = self.subbanddata_set.exclude(hostname="", path="")
        if n_on_cep == n_sbs:
            self.on_cep = "true"
        elif n_on_cep > 0:
            self.on_cep = "partial"
        else:
            self.on_cep = "false"

        self.save()

    def __unicode__(self):
        return self.observation.obsid + " beam " + str(self.beam)

    class Meta:
        ordering = ['observation__start_time', 'beam']


class SubbandData(models.Model):
    # Note that we generate a primary key so that we can bulk insert.
    id = models.CharField(max_length=20, primary_key=True)
    beam = models.ForeignKey(Beam)
    number = models.IntegerField()
    subband = models.ForeignKey(Subband)
    size = models.IntegerField(blank=True, null=True) # Bytes?
    hostname = models.CharField(max_length=20, blank=True)
    path = models.CharField(max_length=150, blank=True)
    archive = models.ForeignKey(ArchiveSite, blank=True, null=True)

    def save(self, *args, **kwargs):
        super(SubbandData, self).save(*args, **kwargs)
        self.beam._update_status()

    def __unicode__(self):
        return self.beam.observation.obsid + " SAP" + str(self.beam.beam) + " SB" + str(self.number)

    class Meta:
        ordering = ['number']
