from django.db import models
from pgvector.django import VectorField

from .common import UUIDTimeStampedModel
from .catalog import Category


class PhysicalBook(UUIDTimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    keywords = models.TextField(blank=True)
    details = models.JSONField(blank=True, null=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=50, unique=True)
    image_path = models.TextField(null=True)
    copies_total = models.IntegerField()
    copies_available = models.IntegerField()
    times_borrowed = models.IntegerField(default=0)
    embedding = VectorField(dimensions=3072, null=True, blank=True)

    def __str__(self):
        return self.title


class BookCopy(UUIDTimeStampedModel):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("borrowed", "Borrowed"),
        ("damaged", "Damaged"),
        ("lost", "Lost"),
    ]

    book = models.ForeignKey(
        PhysicalBook,
        on_delete=models.CASCADE,
        related_name="copies"
    )
    copy_number = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available"
    )
    barcode = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.book.title} - Copy {self.copy_number}"