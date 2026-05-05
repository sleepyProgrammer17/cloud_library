from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField

from .common import UUIDTimeStampedModel
from .catalog import Category, Department



class ResearchRepository(UUIDTimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    title = models.CharField(max_length=255)
    keywords = models.TextField(blank=True)
    best_thesis = models.BooleanField(default=False)
    file_path = models.TextField(null=True)
    details = models.JSONField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    times_viewed = models.IntegerField(default=0)
    embedding = VectorField(dimensions=3072, null=True, blank=True)

    def __str__(self):
        return self.title