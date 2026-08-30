"""Pure SVG badge rendering — no DB/IO, independently testable. Layout is
a flat shields.io-style badge, generated locally rather than depending on
the shields.io service."""

from __future__ import annotations


def _color_for_score(score: int) -> str:
    if score >= 90:
        return "#4c1"  # green
    if score >= 70:
        return "#dfb317"  # yellow
    return "#e05d44"  # red


def render_badge(score: int) -> str:
    color = _color_for_score(score)
    label = "mcphound"
    value = str(score)
    label_width = 62
    value_width = 34
    total_width = label_width + value_width
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" \
role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_width / 2}" y="14">{label}</text>
    <text x="{label_width + value_width / 2}" y="14">{value}</text>
  </g>
</svg>"""
