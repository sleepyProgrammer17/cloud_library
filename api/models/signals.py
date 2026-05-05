from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .books import BookCopy


def _sync_book_counts(book):
    book.copies_total = book.copies.count()
    book.copies_available = book.copies.filter(status="available").count()
    book.save(update_fields=["copies_total", "copies_available"])


@receiver(post_save, sender=BookCopy)
def on_bookcopy_save(sender, instance, **kwargs):
    _sync_book_counts(instance.book)


@receiver(post_delete, sender=BookCopy)
def on_bookcopy_delete(sender, instance, **kwargs):
    _sync_book_counts(instance.book)