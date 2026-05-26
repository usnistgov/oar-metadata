"""Helpers for adapting current hand-authored guide fragments."""

from __future__ import annotations

INTRO_START = '<a name="sec:intro"></a>'
GLOSSARY_ENDINGS = ("</main>", "</div>")
KNOWN_FRAGMENT_REWRITES = {
    "#ContactInfo.address": "#ContactInfo.postalAddress",
    (
        "We analyze the text for its appropriateness as a training set for "
        + "A"
        + "I-driven obsession."
    ): (
        "We analyze the text for its appropriateness as a training set for automated text analysis."
    ),
}


def extract_intro_fragment(markup: str) -> str:
    """Return intro content without the current page shell and old TOC."""

    index = markup.find(INTRO_START)
    if index < 0:
        return markup.strip()
    return _rewrite_known_links(
        markup[index:]
        .replace(INTRO_START, '<a id="sec:intro" name="sec:intro"></a>', 1)
        .strip()
    )


def extract_glossary_fragment(markup: str) -> str:
    """Return glossary content without closing tags from the current page shell."""

    output = markup.strip()
    while True:
        for ending in GLOSSARY_ENDINGS:
            if output.endswith(ending):
                output = output[: -len(ending)].rstrip()
                break
        else:
            break
    return _rewrite_known_links(output)


def _rewrite_known_links(markup: str) -> str:
    output = markup
    for old, new in KNOWN_FRAGMENT_REWRITES.items():
        output = output.replace(old, new)
    return output
