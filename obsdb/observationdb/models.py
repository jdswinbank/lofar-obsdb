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


class ObservationDataManager(models.Manager):
    def good(self):
        # None of the Beams are bad.
        return super(ObservationDataManager, self).exclude(beam__in=Beam.objects.bad())

    def archived(self):
        # None of the Beams are not archived and at least one Beam is
        # archived.
        return super(ObservationDataManager, self).exclude(
            beam__in=Beam.objects.not_archived()
        ).filter(beam__in=Beam.objects.archived()).distinct()


class Observation(models.Model):
    objects = ObservationDataManager()

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

    def __unicode__(self):
        return self.obsid

    @models.permalink
    def get_absolute_url(self):
        return ('observation_detail', [str(self.obsid)])

    @property
    def archived(self):
        return self in Observation.objects.archived()

    class Meta:
        ordering = ['start_time']


class BeamDataManager(models.Manager):
    def with_subband_counts(self):
        return super(BeamDataManager, self).get_query_set().annotate(
            n_sbd=models.Count("subbanddata", distinct=True),
            n_sb=models.Count("subbands", distinct=True)
        )

    def good(self):
        # A Beam is good if it has the right number of SubbandData objects and
        # they, in turn, are all good.
        return self.with_subband_counts().filter(n_sbd=models.F('n_sb')).exclude(
            subbanddata__in=SubbandData.objects.bad()
        )

    def bad(self):
        # A Beam is bad if it has the wrong number of SubbandData objects and/or
        # some of them are bad.
        q = models.Q(subbanddata__in=SubbandData.objects.bad()) | ~models.Q(n_sbd=models.F('n_sb'))
        return self.with_subband_counts().filter(q)

    def archived(self):
        # For the Beam to be archived, we require that at least one
        # SubbandData has been archived, and no SubbandDatas are not archived.
        # Note that Beams which are bad (because they are missing some
        # subbands) can still be archived under this definition.
        return super(BeamDataManager, self).get_query_set().filter(
            subbanddata__in=SubbandData.objects.archived()
        ).distinct().exclude(
            subbanddata__in=SubbandData.objects.not_archived()
        )

    def not_archived(self):
        # For the Beam not to be archived, we require that at least one
        # SubbandData has not been archived
        return super(BeamDataManager, self).get_query_set().filter(
            subbanddata__in=SubbandData.objects.not_archived()
        )


class Beam(models.Model):
    objects = BeamDataManager()
    observation = models.ForeignKey(Observation)
    beam = models.IntegerField()
    field = models.ForeignKey(Field)
    subbands = models.ManyToManyField(Subband)

    def __unicode__(self):
        return self.observation.obsid + " beam " + str(self.beam)

    class Meta:
        ordering = ['observation__start_time', 'beam']


class SubbandDataManager(models.Manager):
    def good(self):
        # "Good" data is either archived or has both a hostname and a path.
        return super(SubbandDataManager, self).get_query_set().filter(
            ~models.Q(archive=None) | ~models.Q(hostname="") & ~models.Q(path="")
        )

    def bad(self):
        # Not archived, and no hostname/path available.
        return super(SubbandDataManager, self).get_query_set().filter(
            models.Q(archive=None) & (models.Q(hostname="") | models.Q(path=""))
        )

    def archived(self):
        return super(SubbandDataManager, self).get_query_set().exclude(archive=None)

    def not_archived(self):
        return super(SubbandDataManager, self).get_query_set().filter(archive=None)


class SubbandData(models.Model):
    objects = SubbandDataManager()
    # Note that we generate a primary key so that we can bulk insert.
    id = models.CharField(max_length=20, primary_key=True)
    beam = models.ForeignKey(Beam)
    number = models.IntegerField()
    subband = models.ForeignKey(Subband)
    size = models.IntegerField(blank=True, null=True) # Bytes?
    hostname = models.CharField(max_length=20, blank=True)
    path = models.CharField(max_length=150, blank=True)
    archive = models.ForeignKey(ArchiveSite, blank=True, null=True)

    def __unicode__(self):
        return self.beam.observation.obsid + " SAP" + str(self.beam.beam) + " SB" + str(self.number)
