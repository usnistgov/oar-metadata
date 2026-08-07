"""Small allowlist-based sanitizer for trusted guide inline HTML."""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from typing import Any


ALLOWED_TAGS = {
    "a",
    "b",
    "br",
    "code",
    "em",
    "i",
    "span",
    "strong",
}
VOID_TAGS = {"br"}
ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "span": {"class"},
}
ALLOWED_CLASSES = {
    "Property reference",
    "Property Reference",
    "Type reference",
    "Type Reference",
}


def sanitize_inline_html(value: Any) -> str:
    """Return safe inline markup for descriptions copied from source metadata."""

    parser = _InlineSanitizer()
    parser.feed("" if value is None else str(value))
    parser.close()
    return parser.html


class _InlineSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    @property
    def html(self) -> str:
        return "".join(self._parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            return

        safe_attrs = self._safe_attrs(tag, attrs)
        attr_text = "".join(
            f' {name}="{escape(value, quote=True)}"'
            for name, value in safe_attrs
        )
        self._parts.append(f"<{tag}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self._parts.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        self._parts.append(escape(data))

    def handle_entityref(self, name: str) -> None:
        self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._parts.append(f"&#{name};")

    def _safe_attrs(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> list[tuple[str, str]]:
        allowed = ALLOWED_ATTRS.get(tag, set())
        safe: list[tuple[str, str]] = []

        for name, value in attrs:
            if name not in allowed or value is None:
                continue
            if name == "href" and not _safe_href(value):
                continue
            if name == "class" and value not in ALLOWED_CLASSES:
                continue
            safe.append((name, value))

        return safe


def _safe_href(value: str) -> bool:
    return (
        value.startswith("#")
        or value.startswith("https://")
        or value.startswith("http://")
    )
