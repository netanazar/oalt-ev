from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_http_methods

from apps.orders.models import Order

from .forms import ProfileUpdateForm, RegisterForm, WarrantyClaimForm
from .models import User, WarrantyClaim
from .pdf import build_warranty_card_pdf
from .tokens import email_verification_token


def _provider_login_url(provider: str):
    try:
        return reverse(f"{provider}_login")
    except NoReverseMatch:
        try:
            return reverse("socialaccount_login", kwargs={"provider": provider})
        except NoReverseMatch:
            return None


def _social_auth_context():
    context = {
        "social_login_enabled": False,
        "social_google_url": None,
        "social_facebook_url": None,
    }
    if not getattr(settings, "SOCIAL_AUTH_AVAILABLE", False):
        return context

    google_enabled = getattr(settings, "SOCIAL_GOOGLE_ENABLED", False)
    facebook_enabled = getattr(settings, "SOCIAL_FACEBOOK_ENABLED", False)
    google_url = _provider_login_url("google") if google_enabled else None
    facebook_url = _provider_login_url("facebook") if facebook_enabled else None

    context.update(
        {
            "social_login_enabled": bool(google_url or facebook_url),
            "social_google_url": google_url,
            "social_facebook_url": facebook_url,
        }
    )
    return context


class UserLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["username"].widget.attrs.update(
            {
                "class": "w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-red-200 focus:border-red-500",
                "placeholder": "Enter username or email",
                "autocomplete": "username",
            }
        )
        form.fields["password"].widget.attrs.update(
            {
                "class": "w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-red-200 focus:border-red-500",
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_social_auth_context())
        return context


class UserRegisterView(View):
    def get(self, request):
        context = {"form": RegisterForm()}
        context.update(_social_auth_context())
        return render(request, "accounts/register.html", context)

    def post(self, request):
        form = RegisterForm(request.POST)
        if not form.is_valid():
            context = {"form": form}
            context.update(_social_auth_context())
            return render(request, "accounts/register.html", context)
        user = form.save()
        self.send_verification_email(user)
        login(request, user)
        messages.success(request, "Account created. Please verify your email.")
        return redirect("accounts:dashboard")

    def send_verification_email(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        verification_link = f"{settings.SITE_BASE_URL}{reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})}"
        send_mail(
            "Verify your Oalt EV account",
            f"Please verify your email: {verification_link}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )


class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
        if email_verification_token.check_token(user, token):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            messages.success(request, "Email verified successfully.")
        else:
            messages.error(request, "Invalid or expired verification link.")
        return redirect("accounts:dashboard")


@login_required
def dashboard(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "items__product")
        .select_related("shipping_address")
    )
    claims = WarrantyClaim.objects.filter(user=request.user).select_related("order")
    profile_form = ProfileUpdateForm(instance=request.user)
    claim_form = WarrantyClaimForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        if action == "profile":
            profile_form = ProfileUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("accounts:dashboard")
            messages.error(request, "Please fix the profile form errors.")
        elif action == "warranty_claim":
            claim_form = WarrantyClaimForm(request.POST, user=request.user)
            if claim_form.is_valid():
                claim = claim_form.save(commit=False)
                claim.user = request.user
                if claim.order.user_id != request.user.id:
                    messages.error(request, "Invalid order selected for claim.")
                else:
                    claim.save()
                    messages.success(request, f"Warranty claim submitted. Claim ID: {claim.claim_number}")
                    return redirect("accounts:dashboard")
            else:
                messages.error(request, "Please fix the warranty claim form errors.")

    context = {
        "orders": orders,
        "claims": claims,
        "profile_form": profile_form,
        "claim_form": claim_form,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def download_warranty_card(request, claim_number):
    claim = (
        WarrantyClaim.objects.filter(claim_number=claim_number, user=request.user)
        .select_related("order", "user")
        .first()
    )
    if not claim:
        messages.error(request, "Warranty claim not found.")
        return redirect("accounts:dashboard")

    pdf_bytes = build_warranty_card_pdf(claim=claim, generated_at=timezone.localtime())
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="warranty-card-{claim.claim_number}.pdf"'
    return response


class UserPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    success_url = "/accounts/password-reset/done/"


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = "/accounts/password-reset/complete/"


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect("core:home")
