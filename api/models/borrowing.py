from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .common import UUIDTimeStampedModel
from .books import BookCopy


class OverdueSetting(UUIDTimeStampedModel):
    fee_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Fee per day: {self.fee_per_day}"


class BorrowedBook(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("borrowed", "Borrowed"),
        ("returned", "Returned"),
        ("overdue", "Overdue")
    ]

    overdue_setting = models.ForeignKey(
        OverdueSetting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    copy = models.ForeignKey(
        BookCopy,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    borrowed_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    is_damaged = models.BooleanField(default=False)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        copy_info = "No Copy" if not self.copy else f"{self.copy.book.title} (Copy {self.copy.copy_number})"
        return f"{self.user.username} - {copy_info}"


class BookSuggestion(UUIDTimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="book_requests"
    )

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_requests"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title