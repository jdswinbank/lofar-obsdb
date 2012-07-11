from django import forms

from observationdb.models import Survey

class PositionSearchForm(forms.Form):
    ra = forms.FloatField()
    dec = forms.FloatField()
    survey = forms.ChoiceField(
        choices=[(s.id, s.name) for s in Survey.objects.all()]
    )

class FieldFilterForm(forms.Form):
    ra = forms.FloatField(required=False)
    dec = forms.FloatField(required=False)
    radius = forms.FloatField(required=False)
    survey = forms.ChoiceField(
        choices=[(s.id, s.name) for s in Survey.objects.all()],
        required=False
    )

