from django.db import models

class Survey(models.Model):
    name = models.CharField(primary_key=True, max_length=100)

class Field(models.Model):
    name = models.CharField(primary_key=True, max_length=100)
    ra = models.FloatField()
    dec = models.FloatField()
    survey = models.ForeignKey(Survey)

class Station(models.Model):
    name = models.CharField(primary_key=True, max_length=10)

class Observation(models.Model):
    obsid = models.CharField(primary_key=True, max_length=10)
    field = models.ForeignKey(Field)
    stations = models.ManyToManyField(Station)
    start_time = models.DateTimeField()
    duration = models.IntegerField() # Always an integral number of seconds?

class Beam(models.Model):
    observation = models.ForeignKey(Observation)
    beam = models.IntegerField()
    calibrators = models.ManyToManyField('self', blank=True)
