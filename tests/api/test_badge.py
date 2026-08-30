from __future__ import annotations

from mcphound.api.badge import render_badge


def test_render_badge_is_green_for_a_high_score():
    svg = render_badge(90)

    assert "#4c1" in svg
    assert svg.strip().startswith("<svg")
    assert svg.strip().endswith("</svg>")


def test_render_badge_is_yellow_for_a_mid_score():
    svg = render_badge(89)

    assert "#dfb317" in svg


def test_render_badge_is_yellow_at_the_low_band_boundary():
    svg = render_badge(70)

    assert "#dfb317" in svg


def test_render_badge_is_red_below_the_yellow_band():
    svg = render_badge(69)

    assert "#e05d44" in svg


def test_render_badge_includes_the_score_value():
    svg = render_badge(87)

    assert ">87<" in svg
