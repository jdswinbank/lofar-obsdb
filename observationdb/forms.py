from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from observationdb.models import Survey

class LookupForm(forms.Form):
    target = forms.CharField(max_length=100)

class FieldFilterForm(forms.Form):
    ra = forms.FloatField(required=False, label="Right Ascension",
        validators=[MaxValueValidator(360), MinValueValidator(0)],
        widget=forms.TextInput(attrs={'class':'input-small'}))
    dec = forms.FloatField(required=False, label="Declination",
        validators=[MaxValueValidator(90), MinValueValidator(0)],
        widget=forms.TextInput(attrs={'class':'input-small'}))
    radius = forms.FloatField(required=False, label="Search Radius",
        validators=[MaxValueValidator(360), MinValueValidator(0)],
        widget=forms.TextInput(attrs={'class':'input-small'}))
    survey = forms.ChoiceField(
        choices=[("", "")] + [(s.id, s.name) for s in Survey.objects.all()],
        required=False
    )
#    targets = forms.BooleanField(initial=True, required=False, label="Show target fields")
#    calibrators = forms.BooleanField(initial=True, required=False, label="Show calibrator fields")


    def clean(self):
        cleaned_data = super(FieldFilterForm, self).clean()
        ra = cleaned_data.get("ra")
        dec = cleaned_data.get("dec")
        radius = cleaned_data.get("radius")
        if 0 < (ra, dec, radius).count(None) < 3:
            raise forms.ValidationError("Please specify all of right ascension, declination and search radius")

        return cleaned_data
