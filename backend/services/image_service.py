import asyncio
import logging
from urllib.parse import quote_plus, urlparse

import httpx
from config import DEFAULT_PEXELS_API_KEY, DEFAULT_UNSPLASH_ACCESS_KEY

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=10.0)
HTTP_LIMITS = httpx.Limits(max_connections=200, max_keepalive_connections=50)
MAX_PER_PAGE = 12
PROVIDER_RETRY_ATTEMPTS = 2
PROVIDER_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
PROVIDER_CONCURRENCY = 48
_provider_semaphore = asyncio.Semaphore(PROVIDER_CONCURRENCY)
_client_lock = asyncio.Lock()
_shared_client: httpx.AsyncClient | None = None


def _is_http_url(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _normalize_query(value: str) -> str:
    return (value or "").strip()


def _dedupe_urls(urls: list[str], limit: int | None = None) -> list[str]:
    seen = set()
    out: list[str] = []
    for raw in urls:
        if not _is_http_url(raw):
            continue
        url = raw.strip()
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if limit is not None and len(out) >= limit:
            break
    return out


async def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        return _shared_client

    async with _client_lock:
        if _shared_client is None or _shared_client.is_closed:
            _shared_client = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                limits=HTTP_LIMITS,
                follow_redirects=True,
            )
    return _shared_client


async def _request_json_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    headers: dict,
    provider_name: str,
    query: str,
) -> dict:
    last_error: Exception | None = None

    for attempt in range(1, PROVIDER_RETRY_ATTEMPTS + 1):
        try:
            async with _provider_semaphore:
                response = await client.get(url, params=params, headers=headers)

            if (
                response.status_code in PROVIDER_RETRYABLE_STATUSES
                and attempt < PROVIDER_RETRY_ATTEMPTS
            ):
                await asyncio.sleep(0.15 * attempt)
                continue

            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e
            if attempt < PROVIDER_RETRY_ATTEMPTS:
                await asyncio.sleep(0.15 * attempt)

    logger.warning("%s search failed for '%s': %s", provider_name, query, last_error)
    return {}


async def search_pexels(
    query: str,
    api_key: str = "",
    page: int = 1,
    per_page: int = 6,
    client: httpx.AsyncClient | None = None,
) -> list[str]:
    """Search Pexels for images. Returns list of image URLs (may be empty)."""
    key = (api_key or DEFAULT_PEXELS_API_KEY).strip()
    if not key:
        logger.info("Pexels API key not configured, skipping")
        return []

    cleaned_query = _normalize_query(query)
    if not cleaned_query:
        return []

    resolved_client = client or await _get_shared_client()
    data = await _request_json_with_retry(
        resolved_client,
        "https://api.pexels.com/v1/search",
        {
            "query": cleaned_query,
            "per_page": min(max(1, per_page), MAX_PER_PAGE),
            "page": max(1, page),
            "orientation": "landscape",
        },
        {"Authorization": key},
        "Pexels",
        cleaned_query,
    )

    if data.get("photos"):
        urls = [
            p["src"]["landscape"]
            for p in data["photos"]
            if p.get("src", {}).get("landscape")
        ]
        return _dedupe_urls(urls)

    return []


async def search_unsplash(
    query: str,
    access_key: str = "",
    page: int = 1,
    per_page: int = 6,
    client: httpx.AsyncClient | None = None,
) -> list[str]:
    """
    Search Unsplash for images. Returns list of image URLs (may be empty).

    Unsplash API requires an Access Key (not Secret Key) for search requests.
    The Access Key is passed as 'Client-ID' in the Authorization header.
    """
    key = (access_key or DEFAULT_UNSPLASH_ACCESS_KEY).strip()
    if not key:
        logger.info("Unsplash Access Key not configured, skipping")
        return []

    cleaned_query = _normalize_query(query)
    if not cleaned_query:
        return []

    resolved_client = client or await _get_shared_client()
    data = await _request_json_with_retry(
        resolved_client,
        "https://api.unsplash.com/search/photos",
        {
            "query": cleaned_query,
            "per_page": min(max(1, per_page), MAX_PER_PAGE),
            "page": max(1, page),
            "orientation": "landscape",
        },
        {"Authorization": f"Client-ID {key}"},
        "Unsplash",
        cleaned_query,
    )

    if data.get("results"):
        urls = [
            p["urls"]["regular"]
            for p in data["results"]
            if p.get("urls", {}).get("regular")
        ]
        return _dedupe_urls(urls)

    return []


async def fetch_images_with_fallback(
    query: str,
    pexels_key: str = "",
    unsplash_access_key: str = "",
    page: int = 1,
    per_page: int = 6,
    allow_placeholder: bool = True,
) -> list[str]:
    """
    Fetch images using fallback chain: Pexels → Unsplash.
    Returns list of image URLs (or placeholders if none).
    """
    cleaned_query = _normalize_query(query) or "slide"
    page = max(1, int(page or 1))
    per_page = min(max(1, int(per_page or 6)), MAX_PER_PAGE)

    client = await _get_shared_client()

    pexels_urls = await search_pexels(
        cleaned_query,
        pexels_key,
        page=page,
        per_page=per_page,
        client=client,
    )
    if pexels_urls:
        logger.info("Images found on Pexels for '%s'", cleaned_query)
        return pexels_urls

    unsplash_urls = await search_unsplash(
        cleaned_query,
        unsplash_access_key,
        page=page,
        per_page=per_page,
        client=client,
    )
    if unsplash_urls:
        logger.info("Images found on Unsplash for '%s'", cleaned_query)
        return unsplash_urls

    if not allow_placeholder:
        logger.warning("No image found for '%s' across Pexels/Unsplash", cleaned_query)
        return []

    logger.warning("No image found for '%s', using placeholder", cleaned_query)
    safe_query = quote_plus(cleaned_query) or "slide"
    return [f"https://picsum.photos/seed/{safe_query}-{i + 1}/1280/720" for i in range(per_page)]


async def fetch_image_with_fallback(
    query: str,
    pexels_key: str = "",
    unsplash_access_key: str = "",
) -> str:
    """
    Fetch a single image using fallback chain: Pexels → Unsplash.
    Returns image URL or a placeholder URL.
    """
    urls = await fetch_images_with_fallback(
        query,
        pexels_key,
        unsplash_access_key,
        page=1,
        per_page=1,
    )
    return urls[0] if urls else ""
