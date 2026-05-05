# api/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS


def get_role(user):
    profile = getattr(user, "userprofile", None)
    return profile.role if profile else None


class IsLibrarian(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) == "librarian"


class LibrarianFullStudentReadOnly(BasePermission):
    """
    Students:
        - GET ✔
        - PATCH ✔
        - POST ✔ (ONLY for search endpoints)

    Teachers & Librarians:
        - full CRUD ✔
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        role = get_role(request.user)

        # ✅ Full access
        if role in ("librarian", "teacher"):
            return True

        # ✅ Student rules
        if role == "student":

            # Allow GET, HEAD, OPTIONS
            if request.method in SAFE_METHODS:
                return True

            # Allow PATCH
            if request.method == "PATCH":
                return True

            # 🔥 Allow POST only for search
            if request.method == "POST":
                return self.is_search_request(view)

        return False

    def is_search_request(self, view):
        """
        Detect if POST is used for search endpoint
        """

        # If using DRF ViewSet with @action
        if hasattr(view, "action"):
            return view.action == "search"

        # Fallback (URL-based)
        return "search" in view.__class__.__name__.lower()


class BorrowedBookPermission(BasePermission):
    """
    Students/Teachers: can borrow (POST) and view own records only
    Librarians: full access to all records
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = get_role(request.user)
        if role == "librarian":
            return True
        return request.method in (*SAFE_METHODS, "POST")

    def has_object_permission(self, request, view, obj):
        if get_role(request.user) == "librarian":
            return True
        return obj.user == request.user


class UserProfilePermission(BasePermission):
    """
    Students/Teachers: view and edit own profile only
    Librarians: full access to all profiles
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if get_role(request.user) == "librarian":
            return True
        return obj.user == request.user


class BookSuggestionPermission(BasePermission):
    """
    Students/Teachers: create suggestions and view own only
    Librarians: full access (approve/reject)
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = get_role(request.user)
        if role == "librarian":
            return True
        return request.method in (*SAFE_METHODS, "POST")

    def has_object_permission(self, request, view, obj):
        if get_role(request.user) == "librarian":
            return True
        return obj.requested_by == request.user
    
