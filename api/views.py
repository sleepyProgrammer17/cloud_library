from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db.models import Q
from .models import (
    Department, Category, PhysicalBook, BookCopy,
    DigitalResource, ResearchRepository, BorrowedBook,
    BookSuggestion, UserProfile, EmailVerificationToken,OverdueSetting
)
from .serializers import (
    DepartmentSerializer, CategorySerializer, UserSerializer,
    PhysicalBookSerializer, BookCopySerializer, DigitalResourceSerializer,
    ResearchRepositorySerializer, BorrowedBookSerializer, UserProfileSerializer,
    BookSuggestionSerializer, RegisterSerializer, LoginSerializer,
    VerifyEmailSerializer, SemanticSearchSerializer, GlobalSearchSerializer,OverdueSerializer
)
from .service.embedding_service import (
    generate_embedding,
    semantic_search_physical_books,
    semantic_search_digital_resources,
    semantic_search_research,
)
from .utils.email import send_verification_email
from .utils.supabase_storage import upload_file, replace_file, delete_file
from .utils.search_assistant import ask_library_assistant
from .permissions import (
    IsLibrarian, LibrarianFullStudentReadOnly,
    BorrowedBookPermission, UserProfilePermission, BookSuggestionPermission,
)
from django.db.models import F

# =========================================================
# Search Utilities
# =========================================================

def tag_results(results, serializer_class, resource_type: str) -> list:
    data = serializer_class(results, many=True).data
    return [{"type": resource_type, **item} for item in data]


def apply_filters(results, *, available_only=False, department=None, category=None):
    if available_only:
        results = [r for r in results if getattr(r, "copies_available", 1) > 0]
    if department:
        results = [r for r in results if r.department and r.department.name == department]
    if category:
        results = [r for r in results if r.category and r.category.name == category]
    return results


# =========================================================
# Auth Views
# =========================================================

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        token_obj = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        send_verification_email(user, token_obj.token)

        return Response(
            {
                "message": "Registration successful. Please check your email to verify your account.",
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token_value = serializer.validated_data["token"]

        try:
            token_obj = EmailVerificationToken.objects.select_related("user").get(token=token_value)
        except EmailVerificationToken.DoesNotExist:
            return Response({"error": "Invalid verification token."}, status=status.HTTP_400_BAD_REQUEST)

        if token_obj.is_expired():
            token_obj.delete()
            return Response(
                {"error": "Verification token has expired. Please register again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        user.is_active = True
        user.save()

        profile = user.userprofile
        profile.is_email_verified = True
        profile.save()

        token_obj.delete()

        return Response({"message": "Email verified successfully. You can now log in."})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response(
                {"error": "Account is not active. Please verify your email."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        profile = getattr(user, "userprofile", None)

        response = Response({
            "user": {
                "id":                user.id,
                "username":          user.username,
                "email":             user.email,
                "role":              profile.role if profile else "student",
                "full_name":         profile.full_name if profile else "",
                "is_email_verified": profile.is_email_verified if profile else False,
            },
        })

        # Refresh token — long-lived, HTTP-only
        # ✅ Fix
        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,        # should be True for security
            secure=True,
            samesite="None",
            max_age=60 * 60,      # ← 1 hour, matches SIMPLE_JWT setting
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,        # should be True for security
            secure=True,
            samesite="None",
            max_age=60 * 60 * 24 * 7,
            path="/",
        )

        return response
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "No refresh token found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        response = Response({"message": "Logged out successfully."})
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        return response


class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "No refresh token provided."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            response = Response({"message": "Token refreshed"})

            # Set new access token cookie
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # set True in production
                samesite="None",
                max_age=60 * 60,  # 1 hour
                path="/",
            )
            return response

        except TokenError:
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
# =========================================================
# Department & Category
# =========================================================

class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, LibrarianFullStudentReadOnly]




class OverdueViewSet(ModelViewSet):
    queryset = OverdueSetting.objects.all()
    serializer_class = OverdueSerializer
    permission_classes = [IsAuthenticated, LibrarianFullStudentReadOnly]


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, LibrarianFullStudentReadOnly]


# =========================================================
# Users (Librarian only)
# =========================================================

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsLibrarian]


# =========================================================
# Physical Books
# =========================================================

def _build_physical_book_text(book: PhysicalBook) -> str:
    parts = [book.title, book.author, book.keywords]
    if book.category:
        parts.append(book.category.name)
    if book.details:
        priority_keys = {"description", "synopsis"}
        for key in priority_keys:
            if book.details.get(key):
                parts.append(str(book.details[key]))
        for key, val in book.details.items():
            if key not in priority_keys:
                parts.append(str(val))
    return " ".join(filter(None, parts))


def _auto_create_copies(book: PhysicalBook):
    existing_count = BookCopy.objects.filter(book=book).count()
    for i in range(existing_count + 1, book.copies_total + 1):
        BookCopy.objects.create(
            book=book,
            copy_number=i,
            status="available",
            barcode=f"{book.isbn}-{str(i).zfill(4)}",
        )

def _upload_physical_cover(request, resource: PhysicalBook, is_update: bool = False):
    image_file    = request.FILES.get("image")
    update_fields = []

    if image_file:
        file_bytes   = image_file.read()
        content_type = image_file.content_type or "image/jpeg"
        if is_update and resource.image_path:
            replace_file(resource.image_path, file_bytes, content_type)
        else:
            path = upload_file(file=file_bytes, content_type=content_type,
                               folder="physical-books/images", filename=image_file.name)
            if path:
                resource.image_path = path
                update_fields.append("image_path")

    if update_fields:
        resource.save(update_fields=update_fields)

def _upload_physical_cover(request, book: PhysicalBook, is_update: bool = False):
    image_file = request.FILES.get("image")  # ✅ get file from request.FILES
    if not image_file:
        return

    file_bytes = image_file.read()
    content_type = image_file.content_type or "image/jpeg"

    if is_update and book.image_path:
        # Replace existing file
        replace_file(book.image_path, file_bytes, content_type)
    else:
        # Upload new file
        path = upload_file(
            file=file_bytes,
            content_type=content_type,
            folder="physical-books/images",
            filename=image_file.name
        )
        if path:
            book.image_path = path
            book.save(update_fields=["image_path"])

class PhysicalBookViewSet(ModelViewSet):
    queryset = PhysicalBook.objects.prefetch_related("copies").all()
    serializer_class = PhysicalBookSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        copies_total = serializer.validated_data.get("copies_total", 0)
        book = serializer.save(copies_available=copies_total)
        
        _auto_create_copies(book)
        _upload_physical_cover(self.request, book, is_update=False)
        
        embedding = generate_embedding(_build_physical_book_text(book))
        if embedding:
            book.embedding = embedding
            book.save(update_fields=["embedding"])

    def perform_update(self, serializer):
        book = serializer.save()
        current_count = BookCopy.objects.filter(book=book).count()

        if book.copies_total > current_count:
            # Add new copies
            _auto_create_copies(book)

        elif book.copies_total < current_count:
            # Remove extra copies — only delete available ones
            excess = current_count - book.copies_total
            copies_to_delete = BookCopy.objects.filter(
                book=book, status="available"
            ).order_by("-copy_number")[:excess]
            
            for copy in copies_to_delete:
                copy.delete()  # signals fire here → counts auto-update

        _upload_physical_cover(self.request, book, is_update=True)

        embedding = generate_embedding(_build_physical_book_text(book))
        if embedding:
            book.embedding = embedding
            book.save(update_fields=["embedding"])

    def perform_destroy(self, instance):
        if instance.image_path:
            delete_file(instance.image_path)
        instance.delete()   
            
    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request):
        user = request.user
        profile = getattr(user, "userprofile", None)
        role = getattr(profile, "role", "student")

        query = request.data.get("query")
        category = request.data.get("category")
        page = int(request.data.get("page", 1))

        queryset = PhysicalBook.objects.all()

        # -------------------------
        # 🎓 STUDENT + 🏫 TEACHER → SEMANTIC
        # -------------------------
        if role in ["student", "teacher"]:
            if query:
                results = semantic_search_physical_books(
                    query=query,
                    top_k=200
                )
            else:
                results = list(queryset.order_by("-created_at"))

            if category:
                results = [
                    r for r in results
                    if r.category and r.category.name == category
                ]

        # -------------------------
        # 📚 LIBRARIAN → FILTER SEARCH
        # -------------------------
        else:
            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(author__icontains=query) |
                    Q(keywords__icontains=query)
                )

            if category:
                queryset = queryset.filter(category__id=category)

            results = list(queryset.order_by("-created_at"))

        # -------------------------
        # 📄 PAGINATION
        # -------------------------
        page_size = 50
        start = (page - 1) * page_size
        end = start + page_size

        paginated = results[start:end]

        serializer = PhysicalBookSerializer(paginated, many=True)

        return Response({
            "page": page,
            "page_size": page_size,
            "total": len(results),
            "results": serializer.data
        })




# =========================================================
# Digital Resources
# =========================================================

def _build_digital_resource_text(resource: DigitalResource) -> str:
    parts = [resource.title, resource.author, resource.type, resource.keywords, str(resource.published_year)]
    if resource.category:
        parts.append(resource.category.name)
    if resource.details:
        priority_keys = {"description", "abstract"}
        for key in priority_keys:
            if resource.details.get(key):
                parts.append(str(resource.details[key]))
        for key, val in resource.details.items():
            if key not in priority_keys:
                parts.append(str(val))
    return " ".join(filter(None, parts))


def _upload_digital_resource_files(request, resource: DigitalResource, is_update: bool = False):
    image_file    = request.FILES.get("image")
    resource_file = request.FILES.get("file")
    update_fields = []

    if image_file:
        file_bytes   = image_file.read()
        content_type = image_file.content_type or "image/jpeg"
        if is_update and resource.image_path:
            replace_file(resource.image_path, file_bytes, content_type)
        else:
            path = upload_file(file=file_bytes, content_type=content_type,
                               folder="digital-resources/images", filename=image_file.name)
            if path:
                resource.image_path = path
                update_fields.append("image_path")

    if resource_file:
        file_bytes   = resource_file.read()
        content_type = resource_file.content_type or "application/octet-stream"
        if is_update and resource.file_path:
            replace_file(resource.file_path, file_bytes, content_type)
        else:
            path = upload_file(file=file_bytes, content_type=content_type,
                               folder="digital-resources/files", filename=resource_file.name)
            if path:
                resource.file_path = path
                update_fields.append("file_path")

    if update_fields:
        resource.save(update_fields=update_fields)


class DigitalResourceViewSet(ModelViewSet):
    queryset = DigitalResource.objects.all()
    serializer_class = DigitalResourceSerializer
    permission_classes = [IsAuthenticated, LibrarianFullStudentReadOnly]

    def perform_create(self, serializer):
        resource = serializer.save()
        _upload_digital_resource_files(self.request, resource, is_update=False)
        embedding = generate_embedding(_build_digital_resource_text(resource))
        if embedding:
            resource.embedding = embedding
            resource.save(update_fields=["embedding"])

    def perform_update(self, serializer):
        resource = serializer.save()
        _upload_digital_resource_files(self.request, resource, is_update=True)
        embedding = generate_embedding(_build_digital_resource_text(resource))
        if embedding:
            resource.embedding = embedding
            resource.save(update_fields=["embedding"])

    def perform_destroy(self, instance):
        if instance.image_path:
            delete_file(instance.image_path)
        if instance.file_path:
            delete_file(instance.file_path)
        instance.delete()


    @action(detail=True, methods=["patch"], url_path="read")
    def increment_view(self, request, pk=None):
        instance = self.get_object()

        DigitalResource.objects.filter(pk=instance.pk).update(
            times_read=F("times_read") + 1
        )

        instance.refresh_from_db()

        return Response({"times_read": instance.times_read}, status=200)

        
    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request):
        user = request.user
        profile = getattr(user, "userprofile", None)
        role = getattr(profile, "role", "student")

        query = request.data.get("query")
        category = request.data.get("category")
        page = int(request.data.get("page", 1))

        queryset = DigitalResource.objects.all()

        # -------------------------
        # 🎓 STUDENT + 🏫 TEACHER → SEMANTIC
        # -------------------------
        if role in ["student", "teacher"]:
            if query:
                results = semantic_search_digital_resources(
                    query=query,
                    top_k=200
                )
            else:
                results = list(queryset.order_by("-created_at"))

            if category:
                results = [
                    r for r in results
                    if r.category and str(r.category.id) == str(category)  # ✅ compare by ID
                ]

        # -------------------------
        # 📚 LIBRARIAN → FILTER SEARCH
        # -------------------------
        else:
            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(author__icontains=query) |
                    Q(keywords__icontains=query)
                )

            if category:
                queryset = queryset.filter(category__id=category) 
 
            results = list(queryset.order_by("-created_at"))

        # -------------------------
        # 📄 PAGINATION
        # -------------------------
        page_size = 50
        start = (page - 1) * page_size
        end = start + page_size

        paginated = results[start:end]

        serializer = DigitalResourceSerializer(paginated, many=True)

        return Response({
            "page": page,
            "page_size": page_size,
            "total": len(results),
            "results": serializer.data
        })


# =========================================================
# Research Repository
# =========================================================

def _build_research_text(research: ResearchRepository) -> str:
    parts = [research.title, research.keywords]
    if research.category:
        parts.append(research.category.name)
    if research.department:
        parts.append(research.department.name)
    if research.details:
        priority_keys = {"abstract", "authors", "year", "description"}
        for key in priority_keys:
            if research.details.get(key):
                parts.append(str(research.details[key]))
        for key, val in research.details.items():
            if key not in priority_keys:
                parts.append(str(val))
    return " ".join(filter(None, parts))


def _upload_research_file(request, research: ResearchRepository, is_update: bool = False):
    research_file = request.FILES.get("file")
    if not research_file:
        return

    file_bytes   = research_file.read()
    content_type = research_file.content_type or "application/pdf"

    if is_update and research.file_path:
        replace_file(research.file_path, file_bytes, content_type)
    else:
        path = upload_file(file=file_bytes, content_type=content_type,
                           folder="research/files", filename=research_file.name)
        if path:
            research.file_path = path
            research.save(update_fields=["file_path"])

from django.db.models import F, Q

class ResearchRepositoryViewSet(ModelViewSet):
    queryset = ResearchRepository.objects.all()
    serializer_class = ResearchRepositorySerializer
    permission_classes = [IsAuthenticated, LibrarianFullStudentReadOnly]

    # -------------------------
    # CREATE
    # -------------------------
    def perform_create(self, serializer):
        research = serializer.save(uploaded_by=self.request.user)
        _upload_research_file(self.request, research, is_update=False)

        embedding = generate_embedding(_build_research_text(research))
        if embedding:
            research.embedding = embedding
            research.save(update_fields=["embedding"])

    # -------------------------
    # UPDATE
    # -------------------------
    def perform_update(self, serializer):
        research = serializer.save()
        _upload_research_file(self.request, research, is_update=True)

        embedding = generate_embedding(_build_research_text(research))
        if embedding:
            research.embedding = embedding
            research.save(update_fields=["embedding"])

    # -------------------------
    # DELETE
    # -------------------------
    def perform_destroy(self, instance):
        if instance.file_path:
            delete_file(instance.file_path)
        instance.delete()

    # -------------------------
    # 👁 VIEW COUNT
    # -------------------------
    @action(detail=True, methods=["patch"], url_path="view")
    def increment_view(self, request, pk=None):
        instance = self.get_object()

        ResearchRepository.objects.filter(pk=instance.pk).update(
            times_viewed=F("times_viewed") + 1
        )

        instance.refresh_from_db()

        return Response({"times_viewed": instance.times_viewed}, status=200)

    # =========================================================
    # 🔍 MAIN SEARCH (POST)
    # =========================================================
    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request):
        user = request.user
        profile = getattr(user, "userprofile", None)
        role = getattr(profile, "role", "student")

        query = request.data.get("query")
        category = request.data.get("category")
        page = int(request.data.get("page", 1))

        queryset = ResearchRepository.objects.all()

        # -------------------------
        # 🎓 STUDENT → SEMANTIC
        # -------------------------
        if role == "student":
            if query:
                results = semantic_search_research(query=query, top_k=200)
            else:
                results = list(queryset.order_by("-created_at"))

            if category:
                results = [
                    r for r in results
                    if r.category and r.category.id == category
                ]

        # -------------------------
        # 🏫 DEPARTMENT HEAD
        # -------------------------
        elif role == "teacher":
            queryset = queryset.filter(department=profile.department)

            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(keywords__icontains=query)
                )

            if category:
                queryset = queryset.filter(category__id=category)

            results = list(queryset.order_by("-created_at"))

        # -------------------------
        # 📚 LIBRARIAN
        # -------------------------
        else:
            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(keywords__icontains=query)
                )

            if category:
                queryset = queryset.filter(category__id=category)

            results = list(queryset.order_by("-created_at"))

        # -------------------------
        # 📄 PAGINATION
        # -------------------------
        page_size = 50   
        start = (page - 1) * page_size
        end = start + page_size

        paginated = results[start:end]

        serializer = ResearchRepositorySerializer(paginated, many=True)

        return Response({
            "page": page,
            "page_size": page_size,
            "total": len(results),
            "results": serializer.data
        })
# =========================================================
# Borrowed Books
# =========================================================

class BorrowedBookViewSet(ModelViewSet):
    serializer_class = BorrowedBookSerializer
    permission_classes = [IsAuthenticated, BorrowedBookPermission]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "userprofile", None), "role", None)
        if role == "librarian":
            return BorrowedBook.objects.all()
        return BorrowedBook.objects.filter(user=user)

    def perform_create(self, serializer):
        copy = serializer.validated_data.get("copy")
        if copy is None:
            raise serializers.ValidationError("A book copy must be specified.")
        if copy.status != "available":
            raise serializers.ValidationError(
                f"Copy {copy.copy_number} is not available (status: {copy.status})."
            )

        # Flip copy status → signal fires → counts update automatically
        copy.status = "borrowed"
        copy.save(update_fields=["status"])

        # Still increment times_borrowed (signals don't handle this)
        copy.book.times_borrowed += 1
        copy.book.save(update_fields=["times_borrowed"])

        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance    = serializer.instance
        prev_status = instance.status
        new_status  = serializer.validated_data.get("status", prev_status)
        updated     = serializer.save()

        if prev_status != "returned" and new_status == "returned":
            copy = updated.copy
            if copy:
                # Flip copy status → signal fires → counts update automatically
                copy.status = "available"
                copy.save(update_fields=["status"])

# =========================================================
# Book Copies
# =========================================================

class BookCopyViewSet(ModelViewSet):
    queryset = BookCopy.objects.all()
    serializer_class = BookCopySerializer
    permission_classes = [IsAuthenticated, LibrarianFullStudentReadOnly]
    http_method_names = ["get", "patch", "head", "options"]


# =========================================================
# User Profiles
# =========================================================

class UserProfileViewSet(ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, UserProfilePermission]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "userprofile", None), "role", None)
        if role == "librarian":
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# =========================================================
# Book Suggestions
# =========================================================

class BookSuggestionViewSet(ModelViewSet):
    serializer_class = BookSuggestionSerializer
    permission_classes = [IsAuthenticated, BookSuggestionPermission]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "userprofile", None), "role", None)
        if role == "librarian":
            return BookSuggestion.objects.all()
        return BookSuggestion.objects.filter(requested_by=user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


# =========================================================
# Global Search Assistant
# =========================================================

class GlobalSearchAssistantView(APIView):
    permission_classes = [AllowAny]
 
    def post(self, request):
        serializer = GlobalSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
        data           = serializer.validated_data
        query          = data["query"]
        top_k          = data["top_k"]
        resource_type  = data.get("type")
        available_only = data["available_only"]
        department     = data.get("department")
        category       = data.get("category")
        use_assistant  = data.get("use_assistant", False)
 
        results = []
 
        # FIX: pass raw query string directly — embedding_service handles it internally
        if not resource_type or resource_type == "physical":
            books = semantic_search_physical_books(query=query, top_k=top_k)
            books = apply_filters(books, available_only=available_only, category=category)
            results += tag_results(books, PhysicalBookSerializer, "physical_book")
 
        if not resource_type or resource_type == "digital":
            digital = semantic_search_digital_resources(query=query, top_k=top_k)
            digital = apply_filters(digital, category=category)
            results += tag_results(digital, DigitalResourceSerializer, "digital_resource")
 
        if not resource_type or resource_type == "research":
            research = semantic_search_research(query=query, top_k=top_k)
            research = apply_filters(research, department=department, category=category)
            results += tag_results(research, ResearchRepositorySerializer, "research")
 
        assistant_response = ask_library_assistant(query, results) if use_assistant else None
 
        return Response({
            "query":     query,
            "count":     len(results),
            "assistant": assistant_response,
            "results":   results,
        })
 