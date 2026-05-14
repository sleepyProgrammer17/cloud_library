
from django.db import models
from .common import UUIDTimeStampedModel


class Department(UUIDTimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Category(UUIDTimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
