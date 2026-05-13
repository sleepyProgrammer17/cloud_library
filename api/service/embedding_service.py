

# api/service/embedding_service.py
"""
Embedding service using Gemini Embeddings API.

Install:
    pip install google-genai python-dotenv

Environment:
    GEMINI_API_KEY=your_api_key_here

Recommended pgvector field size:
    VectorField(dimensions=3072)
"""

import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from django.db.models import F, Value, FloatField, ExpressionWrapper

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "gemini-embedding-001"

_client = None

try:
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")

    _client = genai.Client(api_key=GEMINI_API_KEY)
    print("Gemini client initialized successfully.")
except Exception as exc:
    _client = None
    logger.error("Failed to initialize Gemini client: %s", exc)
    print(f"Failed to initialize Gemini client: {exc}")


def _embed_text(
    text: str,
    task_type: str,
    title: Optional[str] = None,
) -> Optional[List[float]]:
    """
    Internal helper for creating a single embedding.
    Returns None on failure.
    """
    if _client is None:
        logger.warning("Gemini client not initialized; skipping embedding.")
        print("Gemini client not initialized; skipping embedding.")
        return None

    if not text or not text.strip():
        print("Empty text received; skipping embedding.")
        return None

    try:
        config_kwargs = {
            "task_type": task_type,
        }

        if title and task_type == "RETRIEVAL_DOCUMENT":
            config_kwargs["title"] = title

        print(f"Generating embedding | task_type={task_type} | title={title}")

        response = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text.strip(),
            config=types.EmbedContentConfig(**config_kwargs),
        )

        if not response.embeddings:
            print("No embeddings returned from Gemini.")
            return None

        vector = list(response.embeddings[0].values)
        print(f"Embedding generated successfully. Dimension: {len(vector)}")
        return vector

    except Exception as exc:
        logger.warning("Gemini embedding generation failed: %s", exc)
        print(f"Gemini embedding generation failed: {exc}")
        return None


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generic embedding for semantic similarity/search.
    Kept for backward compatibility.
    """
    return _embed_text(text=text, task_type="SEMANTIC_SIMILARITY")


def generate_document_embedding(
    text: str,
    title: Optional[str] = None,
) -> Optional[List[float]]:
    """
    Create an embedding for content stored in the database.
    """
    return _embed_text(
        text=text,
        task_type="RETRIEVAL_DOCUMENT",
        title=title,
    )


def generate_query_embedding(query: str) -> Optional[List[float]]:
    """
    Create an embedding for a user search query.
    """
    return _embed_text(
        text=query,
        task_type="RETRIEVAL_QUERY",
    )


# ── Semantic search helpers (pgvector cosine distance + score) ──────────────

def semantic_search_physical_books(query: str, top_k: int = 5, threshold: float = 0.6):
    from api.models import PhysicalBook
    from pgvector.django import CosineDistance

    print(f"\n[PhysicalBook Search] query={query} | top_k={top_k} | threshold={threshold}")

    query_vector = generate_query_embedding(query)
    if query_vector is None:
        print("[PhysicalBook Search] Query embedding is None.")
        return PhysicalBook.objects.none()

    queryset = (
        PhysicalBook.objects
        .exclude(embedding=None)
        .annotate(
            distance=CosineDistance("embedding", query_vector),
            score=ExpressionWrapper(
                Value(1.0) - F("distance"),
                output_field=FloatField(),
            ),
        )
        .filter(score__gte=threshold)
        .order_by("-score")[:top_k]
    )

    print(f"[PhysicalBook Search] Results found: {queryset.count()}")
    for item in queryset:
        title = getattr(item, "title", "No title")
        print(
            f"[PhysicalBook] title={title} | score={getattr(item, 'score', None):.4f} | "
            f"distance={getattr(item, 'distance', None):.4f}"
        )

    return queryset


def semantic_search_digital_resources(query: str, top_k: int = 5, threshold: float = 0.6):
    from api.models import DigitalResource
    from pgvector.django import CosineDistance

    print(f"\n[DigitalResource Search] query={query} | top_k={top_k} | threshold={threshold}")

    query_vector = generate_query_embedding(query)
    if query_vector is None:
        print("[DigitalResource Search] Query embedding is None.")
        return DigitalResource.objects.none()

    queryset = (
        DigitalResource.objects
        .exclude(embedding=None)
        .annotate(
            distance=CosineDistance("embedding", query_vector),
            score=ExpressionWrapper(
                Value(1.0) - F("distance"),
                output_field=FloatField(),
            ),
        )
        .filter(score__gte=threshold)
        .order_by("-score")[:top_k]
    )

    print(f"[DigitalResource Search] Results found: {queryset.count()}")
    for item in queryset:
        title = getattr(item, "title", "No title")
        print(
            f"[DigitalResource] title={title} | score={getattr(item, 'score', None):.4f} | "
            f"distance={getattr(item, 'distance', None):.4f}"
        )

    return queryset


def semantic_search_research(query: str, top_k: int = 5, threshold: float = 0.6):
    from api.models import ResearchRepository
    from pgvector.django import CosineDistance

    print(f"\n[Research Search] query={query} | top_k={top_k} | threshold={threshold}")

    query_vector = generate_query_embedding(query)
    if query_vector is None:
        print("[Research Search] Query embedding is None.")
        return ResearchRepository.objects.none()

    queryset = (
        ResearchRepository.objects
        .exclude(embedding=None)
        .annotate(
            distance=CosineDistance("embedding", query_vector),
            score=ExpressionWrapper(
                Value(1.0) - F("distance"),
                output_field=FloatField(),
            ),
        )
        .filter(score__gte=threshold)
        .order_by("-score")[:top_k]
    )

    print(f"[Research Search] Results found: {queryset.count()}")
    for item in queryset:
        title = getattr(item, "title", "No title")
        print(
            f"[Research] title={title} | score={getattr(item, 'score', None):.4f} | "
            f"distance={getattr(item, 'distance', None):.4f}"
        )

    return queryset
