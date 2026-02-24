# Oalt EV eCommerce Platform

Production-oriented single-vendor D2C eCommerce platform for **Oalt EV Technology Pvt. Ltd.** built with Django + PostgreSQL + Tailwind templates + Razorpay.

## 1) Folder Structure

```text
Oalt_EV/
  apps/
    accounts/
    blog/
    cart/
    core/
    dealership/
    orders/
    payments/
    products/
  config/
    settings/
      base.py
      local.py
      production.py
    asgi.py
    urls.py
    wsgi.py
  static/
    js/main.js
  templates/
    accounts/
    blog/
    cart/
    core/
    dashboard/
    dealership/
    orders/
    products/
    base.html
  .env.example
  manage.py
  requirements.txt
```

## 2) Core Features Included

- Custom user model with registration/login/email verification/password reset.
- Homepage with premium sections, WhatsApp CTA, and chat placeholder.
- Product catalog with SEO slug URLs, filters, sorting, pagination.
- Product detail with gallery, review flow, WhatsApp enquiry, EMI calculator.
- Cart with quantity updates, coupon support, GST calculation.
- Checkout with address form, order creation, Razorpay order creation, payment verification.
- Payment records, webhook log model, refund service function.
- Dealership application form with DB save + admin notification email.
- Blog list/detail.
- XML sitemap generation.
- Production settings split and env-driven configuration.

## 3) Setup

1. Create and activate venv.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create `.env` from `.env.example`.
4. Create PostgreSQL DB and update env values.
5. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```
6. Create superuser:
```bash
python manage.py createsuperuser
```
7. Run server:
```bash
python manage.py runserver
```

## 4) Tailwind (Template Mode) Setup

This project currently uses Tailwind CDN for fast bootstrapping. For production-grade CSS build:

1. Install Node.js LTS.
2. Initialize:
```bash
npm init -y
npm install -D tailwindcss
npx tailwindcss init
```
3. Set `content` in `tailwind.config.js`:
```js
content: ["./templates/**/*.html", "./apps/**/*.py"]
```
4. Create `static/src/input.css` and compile:
```bash
npx tailwindcss -i ./static/src/input.css -o ./static/dist/output.css --watch
```
5. Replace CDN script in `templates/base.html` with compiled CSS link.

## 5) Razorpay Flow

1. `orders.checkout` creates Order from Cart.
2. `payments.services.create_razorpay_order` creates provider order and persists `Payment`.
3. Template opens Razorpay Checkout using provider order id.
4. `payments.verify_payment` verifies signature and marks payment + order.
5. `payments.webhook` stores webhook events.
6. `payments.services.refund_payment` supports refund API call.

## 6) Deployment (VPS Ready)

1. Use `config.settings.production`.
2. Set production env vars (`DEBUG=False`, secure key, hosts, DB, email, Razorpay).
3. Collect static:
```bash
python manage.py collectstatic --noinput
```
4. Run with Gunicorn/Uvicorn behind Nginx.
5. Terminate SSL at Nginx (Let's Encrypt).
6. Enable process manager (systemd/supervisor) and PostgreSQL backups.

## 7) Security Notes

- CSRF middleware enabled.
- Secure production settings enabled (`SECURE_SSL_REDIRECT`, HSTS, secure cookies).
- Auth-protected order and payment endpoints.
- Role guard for custom dashboard.

## 8) Next Commercial Hardening Steps

1. Add strict webhook HMAC verification.
2. Implement inventory lock and transactional stock decrement.
3. Add async emails (Celery + Redis).
4. Add richer analytics and charting in custom admin panel.
5. Add pytest suite for checkout/payment edge cases.
