from django.db import models

class Survey(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name

class Field(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ra = models.FloatField()
    dec = models.FloatField()
    survey = models.ForeignKey(Survey)

    def __unicode__(self):
        return self.name

class Station(models.Model):
    name = models.CharField(max_length=10, unique=True)

    def __unicode__(self):
        return self.name

class Observation(models.Model):
    obsid = models.CharField(max_length=10, unique=True)
    field = models.ForeignKey(Field)
    stations = models.ManyToManyField(Station)
    start_time = models.DateTimeField()
    duration = models.IntegerField() # Always an integral number of seconds?
    parset = models.TextField()

    def __unicode__(self):
        return self.name

class Beam(models.Model):
    observation = models.ForeignKey(Observation)
    beam = models.IntegerField()
    calibrators = models.ManyToManyField('self', blank=True)

    def __unicode__(self):
        return self.observation.name + " beam " + str(self.beam)
