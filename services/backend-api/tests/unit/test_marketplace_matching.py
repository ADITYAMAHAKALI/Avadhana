"""Unit tests for structured attribute-match scoring (GitHub issue #66,
`app.services.marketplace_matching`). Pure-function tests against plain
ORM model instances constructed in-memory — no DB, no fakes, per the
module's zero-FastAPI/zero-SQLAlchemy-session design (mirrors
`tests/unit/test_commitment_service.py`'s style for the civic-side
service layer).
"""

from datetime import datetime, timezone

from app.models.marketplace.rfp import RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.services.marketplace_matching import (
    filter_hard_constraints,
    rank_attribute_matches,
    score_attribute_match,
    solution_satisfies_hard_constraints,
)


def _requirement(key: str, value: str, weight: float = 1.0, hard: bool = False) -> RFPRequirement:
    return RFPRequirement(
        rfp_id="rfp-1",
        attribute_key=key,
        attribute_value=value,
        weight=weight,
        is_hard_constraint=hard,
    )


def _attribute(solution_id: str, key: str, value: str) -> SolutionAttribute:
    return SolutionAttribute(solution_id=solution_id, attribute_key=key, attribute_value=value)


def _solution(name: str, created_at: datetime | None = None) -> Solution:
    return Solution(
        id=name,
        organization_id="org-provider",
        title=name,
        description="d",
        category_tags=[],
        status="published",
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# --- hard-constraint filtering ---------------------------------------------


def test_solution_without_matching_hard_constraint_attribute_is_dropped():
    requirements = [
        _requirement("certification", "ISO-27001", hard=True),
        _requirement("industry", "logistics", weight=2.0),
    ]
    # Has the soft requirement but not the hard one.
    attrs = [_attribute("s1", "industry", "logistics")]

    assert solution_satisfies_hard_constraints(attrs, requirements) is False

    candidates = [(_solution("s1"), attrs)]
    survivors = filter_hard_constraints(candidates, requirements)
    assert survivors == []


def test_solution_matching_all_hard_constraints_survives_filter():
    requirements = [
        _requirement("certification", "ISO-27001", hard=True),
        _requirement("industry", "logistics", weight=2.0),
    ]
    attrs = [
        _attribute("s1", "certification", "ISO-27001"),
        _attribute("s1", "industry", "logistics"),
    ]
    candidates = [(_solution("s1"), attrs)]

    survivors = filter_hard_constraints(candidates, requirements)
    assert len(survivors) == 1
    assert survivors[0][0].id == "s1"


def test_no_hard_constraints_means_nothing_is_dropped():
    requirements = [_requirement("industry", "logistics", weight=2.0)]
    # Solution matches nothing at all, but there are no hard constraints
    # to fail, so it must survive the filter (scoring will just rank it
    # low separately).
    attrs: list[SolutionAttribute] = []
    candidates = [(_solution("s1"), attrs)]

    survivors = filter_hard_constraints(candidates, requirements)
    assert len(survivors) == 1


# --- weighted attribute-match scoring --------------------------------------


def test_weighted_scoring_produces_expected_ranking():
    requirements = [
        _requirement("industry", "logistics", weight=3.0),
        _requirement("region", "south-india", weight=1.0),
    ]
    # Total weight = 4.0

    # s1 matches both requirements -> score 4/4 = 1.0
    s1_attrs = [
        _attribute("s1", "industry", "logistics"),
        _attribute("s1", "region", "south-india"),
    ]
    # s2 matches only the higher-weighted requirement -> score 3/4 = 0.75
    s2_attrs = [_attribute("s2", "industry", "logistics")]
    # s3 matches only the lower-weighted requirement -> score 1/4 = 0.25
    s3_attrs = [_attribute("s3", "region", "south-india")]

    score1, matched1 = score_attribute_match(s1_attrs, requirements)
    score2, matched2 = score_attribute_match(s2_attrs, requirements)
    score3, matched3 = score_attribute_match(s3_attrs, requirements)

    assert score1 == 1.0
    assert score2 == 0.75
    assert score3 == 0.25
    assert len(matched1) == 2
    assert len(matched2) == 1
    assert len(matched3) == 1

    candidates = [
        (_solution("s3"), s3_attrs),
        (_solution("s1"), s1_attrs),
        (_solution("s2"), s2_attrs),
    ]
    ranked = rank_attribute_matches(candidates, requirements)
    assert [r.solution.id for r in ranked] == ["s1", "s2", "s3"]
    assert [r.score for r in ranked] == [1.0, 0.75, 0.25]


def test_solution_matching_zero_requirements_scores_lowest():
    requirements = [
        _requirement("industry", "logistics", weight=1.0),
        _requirement("region", "south-india", weight=1.0),
    ]
    matching_attrs = [_attribute("s1", "industry", "logistics")]
    non_matching_attrs = [_attribute("s2", "industry", "healthcare")]

    candidates = [
        (_solution("s1"), matching_attrs),
        (_solution("s2"), non_matching_attrs),
    ]
    ranked = rank_attribute_matches(candidates, requirements)

    assert ranked[-1].solution.id == "s2"
    assert ranked[-1].score == 0.0
    assert ranked[-1].matched_requirement_ids == []
    assert ranked[0].solution.id == "s1"
    assert ranked[0].score == 0.5


def test_attribute_value_mismatch_does_not_count_as_a_match():
    # Same key, different value — must not score as a match.
    requirements = [_requirement("industry", "logistics", weight=1.0)]
    attrs = [_attribute("s1", "industry", "healthcare")]

    score, matched = score_attribute_match(attrs, requirements)
    assert score == 0.0
    assert matched == []


def test_zero_total_weight_returns_zero_score_not_a_division_error():
    requirements: list[RFPRequirement] = []
    attrs = [_attribute("s1", "industry", "logistics")]

    score, matched = score_attribute_match(attrs, requirements)
    assert score == 0.0
    assert matched == []


def test_tie_break_is_stable_by_created_at_ascending():
    requirements = [_requirement("industry", "logistics", weight=1.0)]
    attrs = [_attribute("x", "industry", "logistics")]

    later = _solution("later", created_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    earlier = _solution("earlier", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    candidates = [(later, attrs), (earlier, attrs)]

    ranked = rank_attribute_matches(candidates, requirements)
    assert [r.solution.id for r in ranked] == ["earlier", "later"]
