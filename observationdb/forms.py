from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from observationdb.models import Survey

class LookupForm(forms.Form):
    target = forms.CharField(max_length=100)

class FieldFilterForm(forms.Form):
    ra = forms.FloatField(required=False, label="Right Ascension",
        validators=[MaxValueValidator(360), MinValueValidator(0)],
        widget=forms.TextInput(attrs={'style':'width: 100px'}))
    dec = forms.FloatField(required=False, label="Declination",
        validators=[MaxValueValidator(90), MinValueValidator(-90)],
        widget=forms.TextInput(attrs={'style':'width: 100px'}))
    radius = forms.FloatField(required=False, label="Search Radius",
        validators=[MaxValueValidator(360), MinValueValidator(0)],
        widget=forms.TextInput(attrs={'style':'width: 100px'}))
    survey = forms.ModelChoiceField(
        queryset=Survey.objects.all(), required=False, empty_label="[All Surveys]",
        widget=forms.Select(attrs={'style': 'width: 120px'}))
    sort_by = forms.ChoiceField(required=False, label="Sort By",
        choices=(('name', 'Name'), ('ra', 'RA'), ('dec', "Dec"), ('obs', '# Observations')),
        widget=forms.Select(attrs={'style': 'width: 120px'}))
    reverse = forms.BooleanField(required=False, label="Reverse")

    def clean(self):
        cleaned_data = super(FieldFilterForm, self).clean()
        ra = cleaned_data.get("ra")
        dec = cleaned_data.get("dec")
        radius = cleaned_data.get("radius")
        if 0 < (ra, dec, radius).count(None) < 3:
            if not "ra" in self.errors.keys()  \
                or "dec" in self.errors.keys() \
                or "radius" in self.errors.keys():
                raise forms.ValidationError("Please specify all of right ascension, declination and search radius")

        return cleaned_data
