# api/utils/supabase_storage.py

import uuid
import logging
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY
SUPABASE_BUCKET_NAME = settings.SUPABASE_BUCKET_NAME

_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


def _sanitize_filename(filename: str) -> str:
    name = filename.strip()
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w.\-]", "", name)
    name = re.sub(r"_+", "_", name)
    return name or str(uuid.uuid4())


def _build_path(folder: str, filename: str) -> str:
    folder = folder.strip("/")
    filename = filename.strip("/")
    return f"{folder}/{filename}" if folder else filename


def get_signed_url(file_path: str, expires_in: int = 3600) -> str | None:
    if not file_path:
        return None

    clean_path = file_path.lstrip("/")
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{SUPABASE_BUCKET_NAME}/{clean_path}"

  

    try:
        response = requests.post(
            url,
            json={"expiresIn": expires_in},
            headers=_HEADERS,
            timeout=5,
        )

        response.raise_for_status()
        data = response.json()

        signed_path = data.get("signedUrl") or data.get("signedURL")

        if not signed_path:
            print(f"[supabase] get_signed_url WARNING: no signedUrl/signedURL key in response: {data}")
            logger.warning("get_signed_url: unexpected response shape for '%s': %s", clean_path, data)
            return None

 

        if signed_path.startswith("http"):
            print(f"[supabase] get_signed_url final URL (full): {signed_path}")
            return signed_path

        # Supabase returns /object/sign/... (missing /storage/v1) — fix it
        if not signed_path.startswith("/storage/v1"):
            signed_path = f"/storage/v1{signed_path}"

        final_url = f"{SUPABASE_URL}{signed_path}"
        return final_url

    except requests.HTTPError as exc:
        print(f"[supabase] get_signed_url HTTP ERROR {exc.response.status_code}: {exc.response.text}")
        logger.error("get_signed_url: HTTP %s for '%s': %s", exc.response.status_code, clean_path, exc.response.text)
        return None
    except requests.RequestException as exc:
        print(f"[supabase] get_signed_url REQUEST ERROR: {exc}")
        logger.error("get_signed_url: request failed for '%s': %s", clean_path, exc)
        return None


def upload_file(
    file: bytes,
    content_type: str = "application/octet-stream",
    folder: str = "",
    filename: str = "",
) -> str | None:
    if not file:
        return None

    safe_name = _sanitize_filename(filename) if filename else str(uuid.uuid4())
    file_path = _build_path(folder, safe_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET_NAME}/{file_path}"

    print(f"[supabase] upload_file → POST {url}")

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    try:
        response = requests.post(url, data=file, headers=headers, timeout=10)
        print(f"[supabase] upload_file status  : {response.status_code}")
        print(f"[supabase] upload_file response : {response.text}")
        response.raise_for_status()
        print(f"[supabase] upload_file success  : stored at '{file_path}'")
        return file_path
    except requests.HTTPError as exc:
        print(f"[supabase] upload_file HTTP ERROR {exc.response.status_code}: {exc.response.text}")
        logger.error("upload_file: HTTP %s for '%s': %s", exc.response.status_code, file_path, exc.response.text)
        return None
    except requests.RequestException as exc:
        print(f"[supabase] upload_file REQUEST ERROR: {exc}")
        logger.error("upload_file: request failed for '%s': %s", file_path, exc)
        return None


def replace_file(
    file_path: str,
    file: bytes,
    content_type: str = "application/octet-stream",
) -> bool:
    if not file_path or not file:
        return False

    clean_path = file_path.lstrip("/")
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET_NAME}/{clean_path}"

    print(f"[supabase] replace_file → POST {url}")

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        response = requests.post(url, data=file, headers=headers, timeout=10)
        print(f"[supabase] replace_file status  : {response.status_code}")
        print(f"[supabase] replace_file response : {response.text}")
        response.raise_for_status()
        print(f"[supabase] replace_file success  : replaced '{clean_path}'")
        return True
    except requests.HTTPError as exc:
        print(f"[supabase] replace_file HTTP ERROR {exc.response.status_code}: {exc.response.text}")
        logger.error("replace_file: HTTP %s for '%s': %s", exc.response.status_code, clean_path, exc.response.text)
        return False
    except requests.RequestException as exc:
        print(f"[supabase] replace_file REQUEST ERROR: {exc}")
        logger.error("replace_file: request failed for '%s': %s", clean_path, exc)
        return False


def delete_file(file_path: str) -> bool:
    if not file_path:
        return False

    clean_path = file_path.lstrip("/")
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET_NAME}"

    print(f"[supabase] delete_file → DELETE {url} prefixes=['{clean_path}']")

    try:
        response = requests.delete(
            url,
            json={"prefixes": [clean_path]},
            headers=_HEADERS,
            timeout=5,
        )
        print(f"[supabase] delete_file status  : {response.status_code}")
        print(f"[supabase] delete_file response : {response.text}")
        response.raise_for_status()
        print(f"[supabase] delete_file success  : deleted '{clean_path}'")
        return True
    except requests.HTTPError as exc:
        print(f"[supabase] delete_file HTTP ERROR {exc.response.status_code}: {exc.response.text}")
        logger.error("delete_file: HTTP %s for '%s': %s", exc.response.status_code, clean_path, exc.response.text)
        return False
    except requests.RequestException as exc:
        print(f"[supabase] delete_file REQUEST ERROR: {exc}")
        logger.error("delete_file: request failed for '%s': %s", clean_path, exc)
        return False