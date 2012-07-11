from django import forms

from observationdb.models import Survey

class PositionSearchForm(forms.Form):
    ra = forms.FloatField()
    dec = forms.FloatField()
    survey = forms.ChoiceField(
        choices=[(s.id, s.name) for s in Survey.objects.all()]
    )
