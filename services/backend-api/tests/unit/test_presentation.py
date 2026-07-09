"""Unit tests for server-side presentation helpers: initials, avatar
color, relative time."""

from datetime import timedelta

from app.core.presentation import (
    AVATAR_COLOR_PALETTE,
    avatar_color_for_user_id,
    initials_for_name,
    time_ago,
)
from app.core.time import utcnow


def test_initials_two_word_name():
    assert initials_for_name("Ravi Menon") == "RM"


def test_initials_single_word_name():
    assert initials_for_name("Cher") == "CH"


def test_initials_single_letter_name():
    assert initials_for_name("X") == "X"


def test_initials_multi_word_name_uses_first_and_last():
    assert initials_for_name("Anita Kumari Rao") == "AR"


def test_initials_blank_name_falls_back():
    assert initials_for_name("   ") == "?"


def test_avatar_color_is_deterministic_for_same_id():
    color1 = avatar_color_for_user_id("user-123")
    color2 = avatar_color_for_user_id("user-123")
    assert color1 == color2
    assert color1 in AVATAR_COLOR_PALETTE


def test_avatar_color_varies_across_the_fixed_palette():
    # Not a strict requirement that different ids differ, but the
    # palette should actually get used across many ids (sanity check
    # that the hash isn't collapsing everything to one color).
    colors = {avatar_color_for_user_id(f"user-{i}") for i in range(50)}
    assert len(colors) > 1


def test_time_ago_just_now():
    assert time_ago(utcnow()) == "just now"


def test_time_ago_hours():
    moment = utcnow() - timedelta(hours=2)
    assert time_ago(moment) == "2h ago"


def test_time_ago_days():
    moment = utcnow() - timedelta(days=3)
    assert time_ago(moment) == "3d ago"
