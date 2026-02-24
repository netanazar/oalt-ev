from django import forms

from .models import DealershipApplication


class DealershipApplicationForm(forms.ModelForm):
    class Meta:
        model = DealershipApplication
        fields = ["name", "city", "state", "investment_capacity", "phone", "email", "experience"]
