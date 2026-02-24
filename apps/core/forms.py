from django import forms

from apps.products.models import Product

from .models import ContactInquiry, NewsletterSubscriber


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]


class ContactInquiryForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ["name", "email", "phone", "subject", "message"]


class DashboardProductCreateForm(forms.ModelForm):
    listing_status = forms.ChoiceField(
        choices=(("draft", "Draft"), ("published", "Published")),
        initial="published",
        widget=forms.Select(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"}),
    )

    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "short_description",
            "description",
            "price",
            "discount_price",
            "battery_capacity_kwh",
            "range_per_charge_km",
            "stock",
            "main_image",
            "is_featured",
            "meta_title",
            "meta_description",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"}),
            "name": forms.TextInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "placeholder": "Product title"}),
            "short_description": forms.TextInput(
                attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "placeholder": "Short sales pitch"}
            ),
            "description": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "rows": 4, "placeholder": "Full product description"}
            ),
            "price": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "step": "0.01"}),
            "discount_price": forms.NumberInput(
                attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "step": "0.01", "placeholder": "Optional"}
            ),
            "battery_capacity_kwh": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "step": "0.01"}),
            "range_per_charge_km": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"}),
            "stock": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"}),
            "main_image": forms.ClearableFileInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"}),
            "meta_title": forms.TextInput(attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "placeholder": "SEO title (optional)"}),
            "meta_description": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm", "rows": 2, "placeholder": "SEO description (optional)"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["listing_status"].initial = "published" if self.instance.is_active else "draft"

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("price")
        discount_price = cleaned_data.get("discount_price")
        if price is not None and discount_price is not None and discount_price > price:
            self.add_error("discount_price", "Discount price cannot be greater than base price.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        status = self.cleaned_data.get("listing_status", "published")
        instance.is_active = status == "published"
        if commit:
            instance.save()
        return instance
