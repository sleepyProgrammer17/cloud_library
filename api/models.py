# # models.py
# from django.db import models
# from django.contrib.auth.models import User
# import uuid
# from django.utils import timezone
# from pgvector.django import VectorField
# # models.py — add at the very bottom

# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver


# def _sync_book_counts(book):
#     """Single source of truth for copies_total and copies_available."""
#     book.copies_total     = book.copies.count()
#     book.copies_available = book.copies.filter(status="available").count()
#     book.save(update_fields=["copies_total", "copies_available"])




    

# # -------------------------
# # Department
# # -------------------------
# class Department(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name


# # -------------------------
# # Category
# # -------------------------
# class Category(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255)
#     description = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name


# # -------------------------
# # User Profile (extension of Django User)
# # -------------------------
# class UserProfile(models.Model):

#     ROLE_CHOICES = [
#         ("student", "Student"),
#         ("teacher", "Teacher"),
#         ("librarian", "Librarian"),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     user = models.OneToOneField(User, on_delete=models.CASCADE)

#     full_name = models.CharField(max_length=255)

#     role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="student")

#     grant_access = models.BooleanField(default=False)

#     is_email_verified = models.BooleanField(default=False)

#     department = models.ForeignKey(
#         Department,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.full_name


# # -------------------------
# # Email Verification Token
# # -------------------------
# class EmailVerificationToken(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="verification_token")
#     token = models.UUIDField(default=uuid.uuid4, editable=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField()

#     def is_expired(self):
#         return timezone.now() > self.expires_at

#     def __str__(self):
#         return f"Verification token for {self.user.username}"


# # -------------------------
# # Overdue Settings
# # -------------------------
# class OverdueSetting(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     fee_per_day = models.DecimalField(max_digits=10, decimal_places=2)
#     active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Fee per day: {self.fee_per_day}"


# # -------------------------
# # Physical Books
# # -------------------------
# class PhysicalBook(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     category = models.ForeignKey(
#         Category,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     keywords = models.TextField(blank=True)

#     details = models.JSONField(blank=True, null=True)

#     title = models.CharField(max_length=255)

#     author = models.CharField(max_length=255)

#     isbn = models.CharField(max_length=50, unique=True)

#     image_path = models.TextField(null=True)

#     copies_total = models.IntegerField()

#     copies_available = models.IntegerField()

#     times_borrowed = models.IntegerField(default=0)

#     # vector embedding (gemini-embedding-001 → 3072 dims)
#     embedding = VectorField(dimensions=3072, null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title


# # -------------------------
# # Book Copies (auto-generated)
# # -------------------------
# class BookCopy(models.Model):

#     STATUS_CHOICES = [
#         ("available", "Available"),
#         ("borrowed", "Borrowed"),
#         ("damaged", "Damaged"),
#         ("lost", "Lost"),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     book = models.ForeignKey(
#         PhysicalBook,
#         on_delete=models.CASCADE,
#         related_name="copies"
#     )

#     copy_number = models.IntegerField()

#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default="available"
#     )

#     barcode = models.CharField(max_length=100, unique=True)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.book.title} - Copy {self.copy_number}"

# @receiver(post_save, sender=BookCopy)
# def on_bookcopy_save(sender, instance, **kwargs):
#     _sync_book_counts(instance.book)


# @receiver(post_delete, sender=BookCopy)
# def on_bookcopy_delete(sender, instance, **kwargs):
#     _sync_book_counts(instance.book)

    
# # -------------------------
# # Digital Resources
# # -------------------------
# class DigitalResource(models.Model):

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     category = models.ForeignKey(
#         Category,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     keywords = models.TextField(blank=True)

#     title = models.CharField(max_length=255)

#     author = models.CharField(max_length=255)

#     details = models.JSONField(blank=True, null=True)

#     type = models.CharField(max_length=100)

#     image_path = models.TextField(null=True)

#     file_path = models.TextField(null=True)

#     published_year = models.IntegerField()

#     times_read = models.IntegerField(default=0)

    

#     # vector embedding (BAAI/bge-base-en-v1.5 → 768 dims)
#     embedding = VectorField(dimensions=3072, null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title


# # -------------------------
# # Research Repository
# # -------------------------
# class ResearchRepository(models.Model):

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     category = models.ForeignKey(
#         Category,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     title = models.CharField(max_length=255)

#     keywords = models.TextField(blank=True)

#     best_thesis = models.BooleanField(default=False)

#     file_path = models.TextField(null=True)

#     details = models.JSONField(blank=True, null=True)

#     department = models.ForeignKey(Department, on_delete=models.CASCADE)

#     uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

#     times_viewed = models.IntegerField(default=0)

#     # vector embedding (BAAI/bge-base-en-v1.5 → 768 dims)
#     embedding = VectorField(dimensions=3072, null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title


# # -------------------------
# # Borrowed Books
# # -------------------------
# class BorrowedBook(models.Model):

#     STATUS_CHOICES = [
#         ("pending", "Pending"),
#         ("borrowed", "Borrowed"),
#         ("returned", "Returned"),
#         ("overdue", "Overdue")
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     overdue_setting = models.ForeignKey(
#         OverdueSetting,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     user = models.ForeignKey(User, on_delete=models.CASCADE)

#     copy = models.ForeignKey(
#         BookCopy,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True
#     )

#     borrowed_at = models.DateTimeField(default=timezone.now)

#     due_date = models.DateTimeField()

#     returned_at = models.DateTimeField(null=True, blank=True)

#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default="pending"
#     )

#     is_damaged = models.BooleanField(default=False)

#     total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

#     is_paid = models.BooleanField(default=False)

#     paid_at = models.DateTimeField(null=True, blank=True)

#     remarks = models.TextField(blank=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.copy.book.title} (Copy {self.copy.copy_number})"


# class BookSuggestion(models.Model):

#     STATUS_CHOICES = [
#         ("pending", "Pending"),
#         ("approved", "Approved"),
#         ("rejected", "Rejected"),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     requested_by = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name="book_requests"
#     )

#     title = models.CharField(max_length=255)

#     author = models.CharField(max_length=255, blank=True)

#     approved_by = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="approved_requests"
#     )

#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default="pending"
#     )

#     created_at = models.DateTimeField(auto_now_add=True)

#     approved_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return self.title


from .models import *