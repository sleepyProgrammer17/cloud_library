# utils/search_assistant.py

import os
from google import genai


def build_context_from_results(results: list) -> str:
    lines = []
    for item in results:
        resource_type = item.get("type", "unknown")
        title         = item.get("title", "Untitled")
        author        = item.get("author", "")
        keywords      = item.get("keywords", "")
        details       = item.get("details") or {}
        abstract      = details.get("abstract") or details.get("description", "")

        line = f"[{resource_type.upper()}] {title}"
        if author:
            line += f" by {author}"
        if keywords:
            line += f" | Keywords: {keywords}"
        if abstract:
            line += f" | Abstract: {abstract[:300]}"
        lines.append(line)

    return "\n".join(lines)


def ask_library_assistant(query: str, results: list) -> str:
    if not results:
        return "I couldn't find any relevant resources in our library for your query. Try rephrasing or using different keywords."

    context = build_context_from_results(results)

    # Initialize Gemini client
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
You are a helpful library assistant for a university library system in the Philippines.

A student has asked:
"{query}"

Here are the relevant resources found in our library:
{context}

Please:
1. Give a brief, helpful response addressing the student's query
2. Highlight the most relevant resources and why they are useful
3. Group them by type (physical books, digital resources, research/theses)
4. Suggest how the student might use these resources for their study
5. Keep your response concise and friendly

Do not make up resources that are not in the list above.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",  # ⚡ fast + cheap
        contents=prompt
    )

    return response.text