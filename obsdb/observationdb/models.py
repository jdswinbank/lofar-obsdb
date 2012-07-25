from django.db import models
from django.utils.datastructures import SortedDict

from math import sin, cos, acos

EPOCH = "J2000"

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
    archived = models.BooleanField(default=False)
    done = models.BooleanField(default=False)

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
    archived = models.BooleanField(default=False)

    def __unicode__(self):
        return self.obsid

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
    archived = models.BooleanField(default=False)
    good = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Augment save to mark our Observation & Field as archived if all of its subbands are
        # now archived.
        super(Beam, self).save(*args, **kwargs)
        n_archived_beams = self.observation.beam_set.filter(archived=True).count()
        n_good_beams = self.observation.beam_set.filter(good=True).count()

        if n_archived_beams == self.observation.beam_set.count():
            self.observation.archived = True
        else:
            self.observation.archived = False
        if n_good_beams == self.observation.beam_set.count():
            self.observation.good = True
        else:
            self.observation.good = False
        self.observation.save()

        n_archived_beams = self.field.beam_set.filter(archived=True).count()
        n_good_beams = self.field.beam_set.filter(good=True).count()

        if n_archived_beams == self.field.survey.beams_per_field:
            self.field.archived = True
        else:
            self.field.archived = False
        if n_good_beams == self.field.survey.beams_per_field:
            self.field.done = True
        else:
            self.field.done = False
        self.field.save()

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

        # Mark our Beam as archived if all of its subbands are now archived.
        if self.beam.subbanddata_set.exclude(archive=None).count() == self.beam.subbands.count():
            self.beam.archived = True
        else:
            self.beam.archived = False

        # Mark our Beam as good if all of its subbands are either archived or
        # on CEP.
        if self.beam.subbanddata_set.filter(
            ~models.Q(archive=None) | ~models.Q(hostname="") & ~models.Q(path="")
        ).count() == self.beam.subbands.count():
            self.beam.good = True
        else:
            self.beam.good = False

        self.beam.save()

    def __unicode__(self):
        return self.beam.observation.obsid + " SAP" + str(self.beam.beam) + " SB" + str(self.number)
