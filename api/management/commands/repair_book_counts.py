from django.core.management.base import BaseCommand
from api.models import PhysicalBook


class Command(BaseCommand):
    help = "Repair stale copies_total and copies_available counts on PhysicalBook"

    def handle(self, *args, **options):
        repaired = 0
        for book in PhysicalBook.objects.prefetch_related("copies").all():
            correct_total     = book.copies.count()
            correct_available = book.copies.filter(status="available").count()
            if book.copies_total != correct_total or book.copies_available != correct_available:
                book.copies_total     = correct_total
                book.copies_available = correct_available
                book.save(update_fields=["copies_total", "copies_available"])
                repaired += 1
                self.stdout.write(f"  Fixed: {book.title} → total={correct_total}, available={correct_available}")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Repaired {repaired} book(s)."))