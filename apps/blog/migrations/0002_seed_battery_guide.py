from datetime import datetime

from django.db import migrations
from django.utils import timezone


BATTERY_GUIDE_SLUG = "complete-e-cycle-battery-guide-oalt-ev"


BATTERY_GUIDE_CONTENT = """
Complete E-Cycle Battery Guide: Everything You Need to Know About Electric Cycle Batteries

If you own an electric cycle or plan to buy one, the battery is the single most important component to understand. It defines practical range, riding feel, charging routine, and long-term ownership cost.

Why Battery Knowledge Matters

Modern commuters want mobility that is efficient, affordable, and cleaner than fuel-based alternatives. E-cycles deliver that balance, but choosing the right battery setup ensures your experience matches your daily needs.

Core Battery Terms You Should Know

1. Voltage (V):
Higher voltage can provide better power delivery and stronger pickup.

2. Amp-hour (Ah):
Amp-hour indicates how much charge the battery can store.

3. Watt-hour (Wh):
This is total stored energy, calculated as Voltage x Amp-hour.
Example: 36V x 7.8Ah = approximately 280Wh.
Higher Wh usually means more usable range.

Lead-Acid vs Lithium-Ion

Lithium-ion batteries are preferred in modern e-cycles because they are lighter, more efficient, and better for daily city mobility. Lead-acid options may cost less upfront but add significant weight and reduce real-world efficiency.

What Affects E-Cycle Range

Range is not determined by battery capacity alone. It also depends on:
- Rider + load weight
- Pedal assist level and throttle usage
- Route gradient and traffic conditions
- Tyre pressure and riding style
- Weather and battery age

Battery Health and Life: Best Practices

- Charge in moderate room temperature whenever possible.
- Avoid long exposure to high heat.
- Do not keep battery at 0% for long storage periods.
- For storage, maintain around 60% to 80% charge.
- Use genuine charger and compatible charging setup.
- Keep battery connectors clean and dry.

Integrated vs Removable Battery

Integrated Battery:
- Cleaner design
- Better protection from dust and splash
- Lower theft risk

Removable Battery:
- Easy indoor charging
- More apartment-friendly
- Simpler replacement and maintenance workflow

Choose based on your parking, charging access, and daily commute pattern.

How Long Does an E-Cycle Battery Last?

Battery life depends on cell quality, charging habits, and usage conditions. With proper care and timely servicing, an e-cycle battery can remain reliable for years.

How to Choose the Right Battery for Your Use Case

- Daily city commute: choose balanced capacity and lighter setup.
- Long routes: prioritize higher Wh battery.
- Mixed terrain: pair battery capacity with suitable motor and assist tuning.
- Shared family usage: prefer easy charging and low-maintenance configuration.

Cost Planning and Ownership

Battery replacement pricing varies by chemistry, capacity, and build quality. Even then, electric cycles usually offer significantly lower running costs than fuel-powered commuting due to low charging expense and simpler maintenance.

Oalt EV Recommendation

Before buying, evaluate route distance, charging convenience, expected load, and riding style. The right battery + motor combination gives you a smoother, safer, and more economical ride.

Final Takeaway

A good battery is not just about bigger numbers. It is about practical range, consistency, charging convenience, and long-term reliability. Make an informed choice, maintain it properly, and your e-cycle will deliver strong value every day.
"""


def seed_battery_guide(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    published_dt = timezone.make_aware(datetime(2026, 2, 23, 10, 0, 0), timezone.get_current_timezone())
    BlogPost.objects.update_or_create(
        slug=BATTERY_GUIDE_SLUG,
        defaults={
            "title": "Complete E-Cycle Battery Guide: Everything You Need to Know About Electric Cycle Batteries",
            "excerpt": "Learn how to choose the right e-cycle battery, understand range and charging, and extend battery life with practical maintenance tips from Oalt EV.",
            "content": BATTERY_GUIDE_CONTENT.strip(),
            "cover_image": "home/testimonials/Confident_man_with_electric_bicycle.png",
            "is_published": True,
            "published_at": published_dt,
        },
    )


def unseed_battery_guide(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    BlogPost.objects.filter(slug=BATTERY_GUIDE_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_battery_guide, reverse_code=unseed_battery_guide),
    ]

