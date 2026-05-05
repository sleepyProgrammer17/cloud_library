from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField

from .common import UUIDTimeStampedModel
from .catalog import Category, Department


class DigitalResource(UUIDTimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    keywords = models.TextField(blank=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    details = models.JSONField(blank=True, null=True)
    type = models.CharField(max_length=100)
    image_path = models.TextField(null=True)
    file_path = models.TextField(null=True)
    published_year = models.IntegerField()
    times_read = models.IntegerField(default=0)
    embedding = VectorField(dimensions=3072, null=True, blank=True)

    def __str__(self):
        return self.title