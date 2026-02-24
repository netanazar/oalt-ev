from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_admins, send_mail
from django.shortcuts import redirect, render

from .forms import DealershipApplicationForm


def apply(request):
    if request.method == "POST":
        form = DealershipApplicationForm(request.POST)
        if form.is_valid():
            application = form.save()
            body = f"New dealership application from {application.name} ({application.city}, {application.state})"
            mail_admins("New Dealership Application", body, fail_silently=True)
            send_mail("Thanks for applying", "Our team will contact you soon.", settings.DEFAULT_FROM_EMAIL, [application.email], fail_silently=True)
            messages.success(request, "Application submitted successfully.")
            return redirect("dealership:apply")
    else:
        form = DealershipApplicationForm()
    return render(request, "dealership/apply.html", {"form": form})
