from django.db import models


class DealershipApplication(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    investment_capacity = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    experience = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["city", "state", "created_at"])]

    def __str__(self) -> str:
        return f"{self.name} - {self.city}"
