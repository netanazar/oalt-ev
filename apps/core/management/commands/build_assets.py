import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


CRITICAL_SELECTORS = (
    ":root",
    "html",
    "body",
    "a,",
    "a, button",
    ".site-header",
    ".ticker-wrap",
    ".ticker-track",
    ".ticker-row",
    ".amazon-nav-shell",
    ".amazon-nav-top",
    ".amazon-nav-bottom",
    ".mobile-header",
    ".hero-stage-wrap",
    ".hero-slider",
    ".hero-stage",
    ".hero-slide",
    ".hero-dots",
    ".hero-dot",
    ".floating-actions",
    ".floating-action-btn",
    ".hidden",
)

CRITICAL_KEYFRAMES = ("ticker", "luxFadeUp", "luxFadeInRight", "luxGradientMove")


def _iter_css_blocks(source: str):
    cursor = 0
    size = len(source)
    while cursor < size:
        open_brace = source.find("{", cursor)
        if open_brace == -1:
            break
        selector = source[cursor:open_brace].strip()
        depth = 1
        block_start = open_brace + 1
        index = block_start
        while index < size and depth:
            char = source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        if depth == 0:
            block = source[block_start:index - 1]
            yield selector, block
            cursor = index
        else:
            break


def _remove_css_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/", "", source, flags=re.S)


def _minify_css(source: str) -> str:
    css = _remove_css_comments(source)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{}:;,>])\s*", r"\1", css)
    css = css.replace(";}", "}")
    return css.strip() + "\n"


def _minify_js(source: str) -> str:
    minified_lines = []
    for raw_line in source.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        minified_lines.append(stripped)
    return "\n".join(minified_lines).strip() + "\n"


def _extract_critical_css(source: str) -> str:
    blocks = []
    for selector, body in _iter_css_blocks(source):
        selector_lower = selector.lower()
        body_lower = body.lower()
        if selector_lower.startswith("@keyframes") and any(name in selector_lower for name in CRITICAL_KEYFRAMES):
            blocks.append(f"{selector}{{{body}}}")
            continue
        if selector_lower.startswith("@media"):
            if any(hint.lower() in body_lower for hint in CRITICAL_SELECTORS):
                blocks.append(f"{selector}{{{body}}}")
            continue
        if any(hint.lower() in selector_lower for hint in CRITICAL_SELECTORS):
            blocks.append(f"{selector}{{{body}}}")
    blocks.append(".hidden{display:none}")
    return "\n".join(blocks)


class Command(BaseCommand):
    help = "Build minified frontend assets and critical CSS file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-js",
            action="store_true",
            help="Skip JS minification.",
        )
        parser.add_argument(
            "--skip-css",
            action="store_true",
            help="Skip CSS minification and critical extraction.",
        )

    def handle(self, *args, **options):
        static_dir = Path(settings.BASE_DIR) / "static"
        css_source_path = static_dir / "css" / "theme.css"
        js_source_path = static_dir / "js" / "main.js"

        if not css_source_path.exists():
            raise CommandError(f"CSS source not found: {css_source_path}")
        if not js_source_path.exists():
            raise CommandError(f"JS source not found: {js_source_path}")

        if not options["skip_css"]:
            css_source = css_source_path.read_text(encoding="utf-8")
            css_minified = _minify_css(css_source)
            critical_css = _extract_critical_css(css_source)
            critical_minified = _minify_css(critical_css)

            css_min_path = static_dir / "css" / "theme.min.css"
            critical_min_path = static_dir / "css" / "critical.min.css"
            css_min_path.write_text(css_minified, encoding="utf-8")
            critical_min_path.write_text(critical_minified, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Generated {css_min_path}"))
            self.stdout.write(self.style.SUCCESS(f"Generated {critical_min_path}"))

        if not options["skip_js"]:
            js_source = js_source_path.read_text(encoding="utf-8")
            js_minified = _minify_js(js_source)
            js_min_path = static_dir / "js" / "main.min.js"
            js_min_path.write_text(js_minified, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Generated {js_min_path}"))

        self.stdout.write(self.style.SUCCESS("Asset build completed."))
