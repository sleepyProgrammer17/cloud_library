# api/urls.py
# NOTE: This file is mounted under "api/" in library/urls.py,
# so do NOT add an "api/" prefix here — it would result in /api/api/...

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    LogoutView,
    DepartmentViewSet,
    UserViewSet,
    PhysicalBookViewSet,
    BookCopyViewSet,
    DigitalResourceViewSet,
    ResearchRepositoryViewSet,
    BorrowedBookViewSet,
    UserProfileViewSet,
    BookSuggestionViewSet,
    CategoryViewSet,
    GlobalSearchAssistantView,
    CookieTokenRefreshView,
    OverdueViewSet
)

router = DefaultRouter()
router.register(r"overdue",               OverdueViewSet)
router.register(r"departments",           DepartmentViewSet)
router.register(r"category",              CategoryViewSet)
router.register(r"users",                 UserViewSet)
router.register(r"physical-books",        PhysicalBookViewSet)
router.register(r"book-copies",           BookCopyViewSet)
router.register(r"digital-resources",     DigitalResourceViewSet)
router.register(r"research-repositories", ResearchRepositoryViewSet)
router.register(r"borrowed-books",        BorrowedBookViewSet,   basename="borrowedbook")
router.register(r"user-profiles",         UserProfileViewSet,    basename="userprofile")
router.register(r"book-suggestions",      BookSuggestionViewSet, basename="booksuggestion")

urlpatterns = [
    # Swagger / OpenAPI
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Authentication
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token-refresh"),

    path("search/", GlobalSearchAssistantView.as_view(), name="global-search"),

    # Resource CRUD + semantic search
    path("", include(router.urls)),

    # DRF browsable API dev login — /api/auth/browse/login/
    path("auth/browse/", include("rest_framework.urls")),
]