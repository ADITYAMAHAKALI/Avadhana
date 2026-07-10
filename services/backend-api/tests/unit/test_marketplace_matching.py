"""Unit tests for structured attribute-match scoring (GitHub issue #66)
and RRF rank fusion (GitHub issue #68), both in
`app.services.marketplace_matching`. Pure-function tests against plain
ORM model instances / plain dicts constructed in-memory — no DB, no
fakes, per the module's zero-FastAPI/zero-SQLAlchemy-session design
(mirrors `tests/unit/test_commitment_service.py`'s style for the
civic-side service layer).
"""

from datetime import datetime, timezone

from app.models.marketplace.rfp import RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute
from app.services.marketplace_matching import (
    DEFAULT_RRF_K,
    cosine_similarity,
    default_signal_weights,
    filter_hard_constraints,
    fuse_rrf,
    most_recent_vector_by_owner_and_space,
    rank_attribute_matches,
    rank_signal,
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


# --- cosine similarity (issue #68) -----------------------------------


def test_cosine_similarity_identical_vectors_is_one():
    v = [1.0, 2.0, 3.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_similarity_opposite_vectors_is_negative_one():
    assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-9


def test_cosine_similarity_dimension_mismatch_returns_zero_not_raises():
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


def test_cosine_similarity_zero_magnitude_vector_returns_zero_not_raises():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_similarity_empty_vectors_returns_zero():
    assert cosine_similarity([], []) == 0.0


class _FakeEmbedding:
    """Duck-typed stand-in for `EmbeddingVector` — only the fields
    `most_recent_vector_by_owner_and_space` reads."""

    def __init__(self, owner_id, embedding_space, vector, generated_at):
        self.owner_id = owner_id
        self.embedding_space = embedding_space
        self.vector = vector
        self.generated_at = generated_at


def test_most_recent_vector_picks_latest_generated_at_per_owner_and_space():
    old = _FakeEmbedding("sol-1", "summary", [1.0, 0.0], datetime(2026, 1, 1, tzinfo=timezone.utc))
    new = _FakeEmbedding("sol-1", "summary", [0.0, 1.0], datetime(2026, 6, 1, tzinfo=timezone.utc))
    other_space = _FakeEmbedding(
        "sol-1", "technical_spec", [1.0, 1.0], datetime(2026, 3, 1, tzinfo=timezone.utc)
    )
    other_owner = _FakeEmbedding(
        "sol-2", "summary", [2.0, 2.0], datetime(2026, 1, 1, tzinfo=timezone.utc)
    )

    result = most_recent_vector_by_owner_and_space([old, new, other_space, other_owner])

    assert result[("sol-1", "summary")] == [0.0, 1.0]  # newest wins, not insertion order
    assert result[("sol-1", "technical_spec")] == [1.0, 1.0]
    assert result[("sol-2", "summary")] == [2.0, 2.0]


# --- rank_signal (issue #68) -------------------------------------------


def test_rank_signal_orders_descending_by_score():
    scores = {"s1": 0.5, "s2": 0.9, "s3": 0.1}
    ranks = rank_signal(scores)
    assert ranks == {"s2": 1, "s1": 2, "s3": 3}


def test_rank_signal_ties_broken_by_id_ascending():
    scores = {"s2": 0.5, "s1": 0.5}
    ranks = rank_signal(scores)
    assert ranks == {"s1": 1, "s2": 2}


def test_rank_signal_only_ranks_candidates_present_in_scores():
    # A caller who omits a candidate (e.g. missing embedding) must not
    # see it appear in the rank map at all.
    ranks = rank_signal({"s1": 0.9})
    assert set(ranks.keys()) == {"s1"}


# --- default_signal_weights (issue #68) ---------------------------------


def test_default_signal_weights_splits_equally():
    weights = default_signal_weights(["attribute_match", "summary"])
    assert weights == {"attribute_match": 0.5, "summary": 0.5}


def test_default_signal_weights_empty_list_returns_empty_dict():
    assert default_signal_weights([]) == {}


def test_default_signal_weights_single_signal_gets_full_weight():
    assert default_signal_weights(["attribute_match"]) == {"attribute_match": 1.0}


# --- fuse_rrf (issue #68) -----------------------------------------------


def test_fuse_rrf_single_signal_matches_manual_rrf_formula():
    # Two candidates, one signal only. s1 scores higher -> rank 1.
    signal_scores = {
        "s1": {"attribute_match": 0.9},
        "s2": {"attribute_match": 0.2},
    }
    results = fuse_rrf(signal_scores_by_solution=signal_scores)

    by_id = {r.solution_id: r for r in results}
    k = DEFAULT_RRF_K
    # Single signal -> weight 1.0 (default_signal_weights over one name).
    assert abs(by_id["s1"].final_rrf_score - (1.0 / (k + 1))) < 1e-9
    assert abs(by_id["s2"].final_rrf_score - (1.0 / (k + 2))) < 1e-9
    assert by_id["s1"].rank == 1
    assert by_id["s2"].rank == 2
    assert by_id["s1"].signal_ranks == {"attribute_match": 1}
    assert by_id["s2"].signal_ranks == {"attribute_match": 2}


def test_fuse_rrf_combines_two_signals_with_equal_default_weights():
    # s1 wins on attribute_match, s2 wins on the embedding signal.
    # With equal weights (0.5 each) and RRF's diminishing-returns curve,
    # a candidate that's consistently ranked #1-or-#2 across BOTH
    # signals should beat one that's #1 on one signal but absent from
    # the other.
    signal_scores = {
        "s1": {"attribute_match": 0.9, "summary": 0.4},  # rank 1, rank 2
        "s2": {"attribute_match": 0.5, "summary": 0.9},  # rank 2, rank 1
        "s3": {"attribute_match": 0.1},  # rank 3, absent from summary
    }
    results = fuse_rrf(signal_scores_by_solution=signal_scores)
    by_id = {r.solution_id: r for r in results}

    k = DEFAULT_RRF_K
    expected_s1 = 0.5 * (1.0 / (k + 1)) + 0.5 * (1.0 / (k + 2))
    expected_s2 = 0.5 * (1.0 / (k + 2)) + 0.5 * (1.0 / (k + 1))
    expected_s3 = 0.5 * (1.0 / (k + 3))  # only participates in attribute_match

    assert abs(by_id["s1"].final_rrf_score - expected_s1) < 1e-9
    assert abs(by_id["s2"].final_rrf_score - expected_s2) < 1e-9
    assert abs(by_id["s3"].final_rrf_score - expected_s3) < 1e-9
    # s1 and s2 tie on fused score (symmetric), s3 ranks last.
    assert by_id["s3"].rank == 3
    assert {by_id["s1"].rank, by_id["s2"].rank} == {1, 2}


def test_fuse_rrf_missing_embedding_signal_does_not_error_and_still_ranks():
    # A Solution with zero embeddings should still be ranked purely on
    # attribute_match (CLAUDE.md: "handle Solutions that have zero
    # embeddings gracefully").
    signal_scores = {
        "s1": {"attribute_match": 0.9, "summary": 0.9},
        "s2": {"attribute_match": 0.8},  # no "summary" key at all
    }
    results = fuse_rrf(signal_scores_by_solution=signal_scores)
    by_id = {r.solution_id: r for r in results}

    assert "summary" not in by_id["s2"].signal_ranks
    assert "summary" not in by_id["s2"].signal_scores
    assert by_id["s1"].rank == 1
    assert by_id["s2"].rank == 2


def test_fuse_rrf_solution_with_zero_signals_ranks_last_with_zero_score():
    signal_scores = {
        "s1": {"attribute_match": 0.5},
        "s2": {},  # no signals at all
    }
    results = fuse_rrf(signal_scores_by_solution=signal_scores)
    by_id = {r.solution_id: r for r in results}

    assert by_id["s2"].final_rrf_score == 0.0
    assert by_id["s2"].signal_scores == {}
    assert by_id["s2"].signal_ranks == {}
    assert by_id["s1"].rank == 1
    assert by_id["s2"].rank == 2


def test_fuse_rrf_custom_weights_favor_the_weighted_signal():
    signal_scores = {
        "s1": {"attribute_match": 0.9, "summary": 0.1},  # strong on attribute_match
        "s2": {"attribute_match": 0.1, "summary": 0.9},  # strong on summary
    }
    # Heavily weight attribute_match -> s1 should win overall.
    results = fuse_rrf(
        signal_scores_by_solution=signal_scores,
        weights={"attribute_match": 0.9, "summary": 0.1},
    )
    by_id = {r.solution_id: r for r in results}
    assert by_id["s1"].final_rrf_score > by_id["s2"].final_rrf_score
    assert by_id["s1"].rank == 1


def test_fuse_rrf_weight_missing_for_a_signal_treated_as_zero_not_error():
    signal_scores = {
        "s1": {"attribute_match": 0.9, "summary": 0.1},
        "s2": {"attribute_match": 0.1, "summary": 0.9},
    }
    # Only attribute_match has a weight -> summary contributes nothing.
    results = fuse_rrf(
        signal_scores_by_solution=signal_scores,
        weights={"attribute_match": 1.0},
    )
    by_id = {r.solution_id: r for r in results}
    k = DEFAULT_RRF_K
    assert abs(by_id["s1"].final_rrf_score - (1.0 / (k + 1))) < 1e-9
    assert abs(by_id["s2"].final_rrf_score - (1.0 / (k + 2))) < 1e-9


def test_fuse_rrf_custom_k_changes_score_magnitude():
    signal_scores = {"s1": {"attribute_match": 0.9}}
    results_default = fuse_rrf(signal_scores_by_solution=signal_scores)
    results_custom_k = fuse_rrf(signal_scores_by_solution=signal_scores, k=10)

    assert results_custom_k[0].final_rrf_score > results_default[0].final_rrf_score
    assert abs(results_custom_k[0].final_rrf_score - (1.0 / 11)) < 1e-9


def test_fuse_rrf_empty_input_returns_empty_list():
    assert fuse_rrf(signal_scores_by_solution={}) == []
