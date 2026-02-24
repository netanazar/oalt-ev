from django import forms
from django.core.exceptions import ValidationError
import re


class CheckoutAddressForm(forms.Form):
    PAYMENT_METHOD_CHOICES = (
        ("online", "Online Payment (UPI, Cards, Netbanking)"),
        ("cod", "Cash on Delivery (COD)"),
    )

    full_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField()
    address_line1 = forms.CharField(max_length=255)
    address_line2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=120)
    state = forms.CharField(max_length=120)
    postal_code = forms.CharField(max_length=20)
    business_invoice_required = forms.BooleanField(required=False)
    gst_number = forms.CharField(max_length=15, required=False)
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        initial="online",
        widget=forms.RadioSelect,
    )

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 10:
            raise ValidationError("Please enter a valid phone number.")
        return phone

    def clean_postal_code(self):
        postal_code = (self.cleaned_data.get("postal_code") or "").strip()
        digits = "".join(ch for ch in postal_code if ch.isdigit())
        if len(digits) != 6:
            raise ValidationError("Please enter a valid 6-digit postal code.")
        return postal_code

    def clean_gst_number(self):
        gst_number = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if not gst_number:
            return ""
        if not re.match(r"^[0-9A-Z]{15}$", gst_number):
            raise ValidationError("GST number must be 15 characters (alphanumeric).")
        return gst_number

    def clean(self):
        cleaned_data = super().clean()
        business_invoice_required = cleaned_data.get("business_invoice_required")
        gst_number = cleaned_data.get("gst_number", "")
        if business_invoice_required and not gst_number:
            self.add_error("gst_number", "GST number is required when Business Invoice is selected.")
        return cleaned_data
