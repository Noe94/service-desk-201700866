from django import forms

from .models import CI, CIClass, CIRelation, Location


class CIForm(forms.ModelForm):
    class Meta:
        model = CI
        exclude = ["tickets"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2}), "change_description": forms.Textarea(attrs={"rows": 2})}


class CIClassForm(forms.ModelForm):
    class Meta:
        model = CIClass
        fields = ["code", "name", "parent", "source", "is_device"]


class CIRelationForm(forms.ModelForm):
    class Meta:
        model = CIRelation
        fields = ["target", "relation_type"]


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["code", "name"]

