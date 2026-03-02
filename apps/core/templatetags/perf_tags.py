from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()


def _candidate_paths(relative_path: str):
    normalized = relative_path.replace("\\", "/").lstrip("/")
    static_dirs = []
    for static_dir in getattr(settings, "STATICFILES_DIRS", []):
        try:
            static_dirs.append(Path(static_dir))
        except TypeError:
            continue
    if getattr(settings, "STATIC_ROOT", None):
        static_dirs.append(Path(settings.STATIC_ROOT))
    for base in static_dirs:
        yield base / normalized


@lru_cache(maxsize=128)
def _asset_exists(relative_path: str) -> bool:
    return any(path.exists() and path.is_file() for path in _candidate_paths(relative_path))


@lru_cache(maxsize=16)
def _read_static_source(relative_path: str) -> str:
    for path in _candidate_paths(relative_path):
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def _with_min_suffix(path: str) -> str:
    if path.endswith(".min.css") or path.endswith(".min.js"):
        return path
    if path.endswith(".css"):
        return f"{path[:-4]}.min.css"
    if path.endswith(".js"):
        return f"{path[:-3]}.min.js"
    return path


def _latest_mtime(relative_path: str) -> float:
    latest = 0.0
    for path in _candidate_paths(relative_path):
        if path.exists() and path.is_file():
            latest = max(latest, path.stat().st_mtime)
    return latest


@register.simple_tag
def asset_path(path: str) -> str:
    use_min = getattr(settings, "ASSET_MINIFY_ENABLED", False)
    target = path
    if use_min:
        min_path = _with_min_suffix(path)
        if min_path != path and _asset_exists(min_path):
            # Serve minified file only when it is not stale compared to source.
            # This prevents broken UI when source CSS/JS is updated but min asset
            # has not been rebuilt yet.
            source_mtime = _latest_mtime(path)
            min_mtime = _latest_mtime(min_path)
            if min_mtime and (source_mtime == 0 or min_mtime >= source_mtime):
                target = min_path
    asset_url = static(target)
    version = getattr(settings, "ASSET_VERSION", "").strip()
    if version:
        separator = "&" if "?" in asset_url else "?"
        asset_url = f"{asset_url}{separator}v={version}"
    return asset_url


@register.simple_tag
def critical_css_inline() -> str:
    critical_path = getattr(settings, "CRITICAL_CSS_FILE", "css/critical.min.css")
    critical_css = _read_static_source(critical_path)
    if not critical_css:
        fallback_source = _read_static_source("css/theme.css")
        critical_css = fallback_source[:4000]
    return mark_safe(critical_css)
