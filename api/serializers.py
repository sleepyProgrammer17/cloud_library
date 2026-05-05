# serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import (
    Department,
    Category,
    PhysicalBook,
    BookCopy,
    DigitalResource,
    ResearchRepository,
    BorrowedBook,
    UserProfile,
    BookSuggestion,
    OverdueSetting,
    EmailVerificationToken,
)
from .utils.supabase_storage import get_signed_url


# -------------------------
# Auth Serializers
# -------------------------

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")
    full_name = serializers.CharField(required=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "full_name", "department"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email is already in use."})
        return attrs

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        department = validated_data.pop("department", None)
        validated_data.pop("password2")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
        )

        UserProfile.objects.create(
            user=user,
            full_name=full_name,
            role="student",
            department=department,
        )

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)


# -------------------------
# Department
# -------------------------
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"



class OverdueSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverdueSetting
        fields = "__all__"
# -------------------------
# User
# -------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


# -------------------------
# Physical Books
# -------------------------
class BookCopySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCopy
        fields = "__all__"
        read_only_fields = ["id", "copy_number", "barcode", "created_at"]


class PhysicalBookSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)
    signed_image_url = serializers.SerializerMethodField(read_only=True)
    category_name   = serializers.CharField(source="category.name", read_only=True)    # was missing
    copies = BookCopySerializer(many=True, read_only=True)

    class Meta:
        model = PhysicalBook
        fields = "__all__"
        read_only_fields = ["id", "embedding", "created_at", "copies_available", "times_borrowed","image_path","signed_image_url","category_name"]

    def get_signed_image_url(self, obj: DigitalResource) -> str | None:
        return get_signed_url(obj.image_path, expires_in=3600)


    def create(self, validated_data):
        validated_data.pop("image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("image", None)
        return super().update(instance, validated_data)

# -------------------------
# Digital Resources
# -------------------------
class DigitalResourceSerializer(serializers.ModelSerializer):
    """
    Write-only upload fields (multipart/form-data):
      - `image`  → cover image file; popped before ORM save, uploaded to Supabase
                   by the view, path stored back into `image_path`.
      - `file`   → resource file (PDF/EPUB/…); same pattern into `file_path`.

    Read-only response fields:
      - `image_path` / `file_path`             → raw bucket paths (set by view).
      - `signed_image_url` / `signed_file_url` → 1-hour signed URLs, generated
                                                  fresh on every serialization.
    """

    image = serializers.ImageField(write_only=True, required=False, allow_null=True)
    file  = serializers.FileField(write_only=True,  required=False, allow_null=True)
    category_name   = serializers.CharField(source="category.name", read_only=True)    # was missing
    signed_image_url = serializers.SerializerMethodField(read_only=True)
    signed_file_url  = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DigitalResource
        fields = "__all__"
        read_only_fields = [
            "id",
            "embedding",
            "created_at",
            "times_read",
            "category_name",
            "image_path",
            "file_path",
            "signed_image_url",
            "signed_file_url",
        ]

    def get_signed_image_url(self, obj: DigitalResource) -> str | None:
        return get_signed_url(obj.image_path, expires_in=3600)

    def get_signed_file_url(self, obj: DigitalResource) -> str | None:
        return get_signed_url(obj.file_path, expires_in=3600)

    def create(self, validated_data):
        # Remove upload fields — they are not model fields and must never reach
        # the ORM. The view retrieves them via self.context and handles the upload.
        validated_data.pop("image", None)
        validated_data.pop("file", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Same removal on update.
        validated_data.pop("image", None)
        validated_data.pop("file", None)
        return super().update(instance, validated_data)


# -------------------------
# Research Repository
# -------------------------
class ResearchRepositorySerializer(serializers.ModelSerializer):
    """
    Write-only upload field (multipart/form-data):
      - `file` → thesis/research PDF; popped before ORM save, uploaded to Supabase
                 by the view, path stored back into `file_path`.

    Read-only response fields:
      - `file_path`            → raw bucket path (set by view).
      - `signed_file_url`      → 1-hour signed URL, generated fresh on every serialization.
      - `uploaded_by_username` → uploader's username for display.
    """

    file = serializers.FileField(write_only=True, required=False, allow_null=True)

    signed_file_url      = serializers.SerializerMethodField(read_only=True)
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    category_name   = serializers.CharField(source="category.name", read_only=True)    # was missing
    department_name = serializers.CharField(source="department.name", read_only=True)  # was missing
    class Meta:
        model = ResearchRepository
        fields = "__all__"
        read_only_fields = [
            "id",
            "embedding",
            "created_at",
            "times_viewed",
            "uploaded_by",
            "file_path",
            "signed_file_url",
            "category_name",
            "department_name",
        ]
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep.pop("embedding", None)  # ✅ strip from all responses
        return rep

    def get_signed_file_url(self, obj: ResearchRepository) -> str | None:
        return get_signed_url(obj.file_path, expires_in=3600)

    def create(self, validated_data):
        # Remove upload field before ORM save; view handles the actual upload.
        validated_data.pop("file", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Same removal on update.
        validated_data.pop("file", None)
        return super().update(instance, validated_data)


# -------------------------
# Borrowed Books
# -------------------------
class BorrowedBookSerializer(serializers.ModelSerializer):
    user        = serializers.StringRelatedField(read_only=True)
    book_title  = serializers.CharField(source="copy.book.title",  read_only=True)
    book_author = serializers.CharField(source="copy.book.author", read_only=True)

    class Meta:
        model  = BorrowedBook
        fields = [
            "id",
            "user",
            "copy",
            "book_title",
            "book_author",
            "overdue_setting",
            "borrowed_at",
            "due_date",
            "returned_at",
            "status",
            "is_damaged",
            "total_fee",
            "is_paid",
            "paid_at",
            "remarks",
        ]
        read_only_fields = ["id", "user", "total_fee", "paid_at", "book_title", "book_author"]
# -------------------------
# User Profile
# -------------------------
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "is_email_verified"]


# -------------------------
# Book Suggestion
# -------------------------
class BookSuggestionSerializer(serializers.ModelSerializer):
    requested_by_username = serializers.CharField(source="requested_by.username", read_only=True)
    approved_by_username  = serializers.CharField(
        source="approved_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = BookSuggestion
        fields = "__all__"
        read_only_fields = ["id", "requested_by", "approved_by", "created_at", "approved_at"]


# -------------------------
# Semantic Search
# -------------------------
class SemanticSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, max_length=500)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=50)





class GlobalSearchSerializer(serializers.Serializer):
    query          = serializers.CharField(required=True, max_length=500)
    top_k          = serializers.IntegerField(required=False, default=10, min_value=1, max_value=50)
    type           = serializers.ChoiceField(
                         choices=["physical", "digital", "research"],
                         required=False,
                         allow_null=True,
                         default=None,
                     )
    available_only = serializers.BooleanField(required=False, default=False)
    department     = serializers.CharField(required=False, allow_null=True, default=None)
    category       = serializers.CharField(required=False, allow_null=True, default=None)
    use_assistant  = serializers.BooleanField(required=False, default=False)