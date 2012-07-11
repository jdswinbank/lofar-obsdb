from django import forms

from observationdb.models import Survey

class FieldFilterForm(forms.Form):
    ra = forms.FloatField(required=False, label="Right Ascension")
    dec = forms.FloatField(required=False, label="Declination")
    radius = forms.FloatField(required=False, label="Search Radius")
#    survey = forms.ChoiceField(
#        choices=[(s.id, s.name) for s in Survey.objects.all()],
#        required=False
#    )
