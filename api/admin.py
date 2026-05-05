from django.contrib import admin
from .models import (
    Department,
    Category,
    UserProfile,
    EmailVerificationToken,
    OverdueSetting,
    PhysicalBook,
    BookCopy,
    DigitalResource,
    ResearchRepository,
    BorrowedBook,
    BookSuggestion,
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "user",
        "role",
        "grant_access",
        "is_email_verified",
        "department",
        "created_at",
    )
    search_fields = ("full_name", "user__username", "user__email")
    list_filter = ("role", "grant_access", "is_email_verified", "department")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "token", "created_at", "expires_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("token", "created_at")


@admin.register(OverdueSetting)
class OverdueSettingAdmin(admin.ModelAdmin):
    list_display = ("id", "fee_per_day", "active", "created_at")
    list_filter = ("active",)


class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 0


@admin.register(PhysicalBook)
class PhysicalBookAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "isbn",
        "category",
        "copies_total",
        "copies_available",
        "times_borrowed",
        "created_at",
    )
    search_fields = ("title", "author", "isbn", "keywords")
    list_filter = ("category", "created_at")
    inlines = [BookCopyInline]
    exclude = ("embedding",)


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ("id", "book", "copy_number", "status", "barcode", "created_at")
    search_fields = ("book__title", "barcode")
    list_filter = ("status", "created_at")


@admin.register(DigitalResource)
class DigitalResourceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "type",
        "category",
        "published_year",
        "times_read",
        "created_at",
    )
    search_fields = ("title", "author", "type", "keywords")
    list_filter = ("category", "type", "published_year")
    exclude = ("embedding",)


@admin.register(ResearchRepository)
class ResearchRepositoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "department",
        "uploaded_by",
        "best_thesis",
        "times_viewed",
        "created_at",
    )
    search_fields = ("title", "keywords", "uploaded_by__username")
    list_filter = ("category", "department", "best_thesis", "created_at")
    exclude = ("embedding",)


@admin.register(BorrowedBook)
class BorrowedBookAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "copy",
        "borrowed_at",
        "due_date",
        "returned_at",
        "status",
        "is_damaged",
        "total_fee",
        "is_paid",
    )
    search_fields = ("user__username", "copy__book__title", "copy__barcode")
    list_filter = ("status", "is_damaged", "is_paid", "borrowed_at", "due_date")


@admin.register(BookSuggestion)
class BookSuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "requested_by",
        "approved_by",
        "status",
        "created_at",
        "approved_at",
    )
    search_fields = ("title", "author", "requested_by__username")
    list_filter = ("status", "created_at", "approved_at")