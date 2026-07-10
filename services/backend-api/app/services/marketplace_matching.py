"""Structured attribute-match scoring for the Marketplace matching engine
(GitHub issue #66, "Structured attribute-match scoring (no ML)") — the
deterministic, non-ML first step of CLAUDE.md "Solution Marketplace
Architecture" -> "Matching engine: multi-attribute, multi-embedding RRF
fusion", steps 1-2:

1. Hard-constraint filtering: drop any Solution that fails to satisfy
   every `is_hard_constraint=True` RFPRequirement.
2. Attribute-match scoring: weighted overlap between the remaining
   candidates' SolutionAttribute rows and the RFP's RFPRequirement rows.

Deliberately has zero FastAPI/HTTP/SQLAlchemy dependency — plain
functions over plain lists of ORM model instances (or anything
duck-typed the same way), mirroring `app/services/commitment_service.py`
so this is unit-testable with in-memory objects (no DB, no fakes needed
beyond constructing the models directly).

Embeddings/cosine-similarity signals and RRF fusion across signals are
explicitly out of scope here — see issues #67 (embeddings) and #68 (RRF
fusion), which will combine this module's score with theirs later. This
module only ever produces the single "attribute-match" signal.
"""

from dataclasses import dataclass

from app.models.marketplace.rfp import RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute


@dataclass(frozen=True)
class AttributeMatchResult:
    """One Solution's outcome against a single RFP's requirements."""

    solution: Solution
    score: float
    matched_requirement_ids: list[str]


def solution_satisfies_hard_constraints(
    solution_attributes: list[SolutionAttribute],
    requirements: list[RFPRequirement],
) -> bool:
    """True iff `solution_attributes` has, for every hard-constraint
    requirement, at least one attribute with the same `attribute_key`
    AND `attribute_value`. Non-hard requirements are ignored here —
    they only affect the weighted score, not eligibility."""
    hard_requirements = [r for r in requirements if r.is_hard_constraint]
    if not hard_requirements:
        return True

    attr_pairs = {(a.attribute_key, a.attribute_value) for a in solution_attributes}
    return all((r.attribute_key, r.attribute_value) in attr_pairs for r in hard_requirements)


def filter_hard_constraints(
    candidates: list[tuple[Solution, list[SolutionAttribute]]],
    requirements: list[RFPRequirement],
) -> list[tuple[Solution, list[SolutionAttribute]]]:
    """Drops every (Solution, attributes) candidate that fails
    `solution_satisfies_hard_constraints` against `requirements`. Cheap,
    deterministic, no ML — CLAUDE.md matching-engine step 1."""
    return [
        (solution, attrs)
        for solution, attrs in candidates
        if solution_satisfies_hard_constraints(attrs, requirements)
    ]


def score_attribute_match(
    solution_attributes: list[SolutionAttribute],
    requirements: list[RFPRequirement],
) -> tuple[float, list[str]]:
    """Weighted overlap score for one Solution against one RFP's
    requirements (CLAUDE.md matching-engine step 2: "Structured
    attribute-match score: deterministic, weighted overlap ... no ML
    involved").

    For every requirement (hard or soft — both count toward the
    weighted sum, only hard ones additionally gate eligibility via
    `solution_satisfies_hard_constraints`), if the Solution has a
    SolutionAttribute with the same `attribute_key` AND `attribute_value`,
    that requirement's `weight` is added to the raw score.

    Normalization: raw score / sum(requirement weights), i.e. "fraction
    of the RFP's total requested weight this Solution satisfies" — a
    score of 1.0 means every requirement matched, 0.0 means none did.
    This choice (over e.g. normalizing by the Solution's own attribute
    count) keeps the score comparable across Solutions with wildly
    different attribute-list sizes, since the denominator is fixed per
    RFP rather than varying per candidate. If an RFP has zero
    requirements, there's nothing to score against — returns (0.0, [])
    rather than dividing by zero or treating "no requirements" as a
    perfect match.

    Returns `(normalized_score, matched_requirement_ids)` — the id list
    backs the "why did this match" explainability CLAUDE.md calls out
    for `SolutionMatch.signal_scores` (that table isn't built yet, but
    the matched-ids breakdown is included now so callers/tests can
    inspect it without re-deriving it).
    """
    total_weight = sum(r.weight for r in requirements)
    if total_weight <= 0:
        return 0.0, []

    attr_pairs = {(a.attribute_key, a.attribute_value) for a in solution_attributes}

    raw_score = 0.0
    matched_ids: list[str] = []
    for requirement in requirements:
        if (requirement.attribute_key, requirement.attribute_value) in attr_pairs:
            raw_score += requirement.weight
            matched_ids.append(requirement.id)

    return raw_score / total_weight, matched_ids


def rank_attribute_matches(
    candidates: list[tuple[Solution, list[SolutionAttribute]]],
    requirements: list[RFPRequirement],
) -> list[AttributeMatchResult]:
    """Full pipeline: hard-constraint filter, then weighted score, then
    sort descending by score (ties broken by `Solution.created_at`
    ascending — earlier-published Solutions rank first, an arbitrary but
    stable tiebreak so results aren't order-dependent on dict/set
    iteration).

    `candidates` is a list of (Solution, its SolutionAttribute rows) —
    the caller is responsible for gathering candidate Solutions (e.g.
    "published" status) and their attributes; this function has no
    repository/DB access of its own, per the module's no-FastAPI/no-ORM
    -session-dependency design.
    """
    survivors = filter_hard_constraints(candidates, requirements)

    results = []
    for solution, attrs in survivors:
        score, matched_ids = score_attribute_match(attrs, requirements)
        results.append(
            AttributeMatchResult(solution=solution, score=score, matched_requirement_ids=matched_ids)
        )

    results.sort(key=lambda r: (-r.score, r.solution.created_at))
    return results
