from django.dispatch import receiver


def _mark_user_email_verified(user):
    if not hasattr(user, "is_email_verified"):
        return
    if user.is_email_verified:
        return
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])


try:
    from allauth.account.signals import email_confirmed, user_signed_up
except Exception:  # pragma: no cover - allauth optional
    email_confirmed = None
    user_signed_up = None


if user_signed_up is not None:
    @receiver(user_signed_up)
    def set_verified_on_social_signup(request, user, **kwargs):
        _mark_user_email_verified(user)


if email_confirmed is not None:
    @receiver(email_confirmed)
    def set_verified_on_email_confirmation(request, email_address, **kwargs):
        user = getattr(email_address, "user", None)
        if user:
            _mark_user_email_verified(user)
