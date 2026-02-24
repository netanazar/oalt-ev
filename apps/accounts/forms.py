from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from datetime import timedelta

from apps.orders.models import Order

from .models import User, WarrantyClaim


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input_class = "w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-red-200 focus:border-red-500"
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = base_input_class
            if field_name == "username":
                field.widget.attrs["placeholder"] = "Choose username"
            elif field_name == "first_name":
                field.widget.attrs["placeholder"] = "First name"
            elif field_name == "last_name":
                field.widget.attrs["placeholder"] = "Last name"
            elif field_name == "email":
                field.widget.attrs["placeholder"] = "you@example.com"
            elif field_name == "phone":
                field.widget.attrs["placeholder"] = "+91 7291880088"
            elif field_name == "password1":
                field.widget.attrs["placeholder"] = "Create password"
            elif field_name == "password2":
                field.widget.attrs["placeholder"] = "Confirm password"


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input_class = "w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-red-200 focus:border-red-500"
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = base_input_class
            if field_name == "first_name":
                field.widget.attrs["placeholder"] = "First name"
            elif field_name == "last_name":
                field.widget.attrs["placeholder"] = "Last name"
            elif field_name == "email":
                field.widget.attrs["placeholder"] = "you@example.com"
            elif field_name == "phone":
                field.widget.attrs["placeholder"] = "+91 7291880088"


class WarrantyClaimForm(forms.ModelForm):
    class Meta:
        model = WarrantyClaim
        fields = ("order", "warranty_card_number", "product_name", "issue_description")
        widgets = {
            "issue_description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        base_input_class = "w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-red-200 focus:border-red-500"
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = base_input_class
        self.fields["order"].queryset = Order.objects.none()
        if user is not None and getattr(user, "is_authenticated", False):
            self.fields["order"].queryset = user.orders.order_by("-created_at")
        self.fields["order"].empty_label = "Select Order"
        self.fields["warranty_card_number"].widget.attrs["placeholder"] = "Enter warranty card number"
        self.fields["product_name"].widget.attrs["placeholder"] = "Product model name"
        self.fields["issue_description"].widget.attrs["placeholder"] = "Describe the issue you are facing"

    def clean_order(self):
        order = self.cleaned_data.get("order")
        if not order:
            return order

        if order.status != Order.Status.DELIVERED:
            raise forms.ValidationError("Warranty claim can be submitted only after order is marked as delivered.")

        if not self.instance.pk:
            claim_deadline = order.updated_at + timedelta(days=7)
            if timezone.now() > claim_deadline:
                raise forms.ValidationError(
                    f"Warranty claim window expired on {timezone.localtime(claim_deadline):%d %b %Y}. "
                    "Claim must be submitted within 7 days of delivery."
                )
        return order
