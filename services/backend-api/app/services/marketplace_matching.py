"""Structured attribute-match scoring + RRF rank-fusion for the
Marketplace matching engine (GitHub issues #66 and #68). Implements all
5 steps of CLAUDE.md "Solution Marketplace Architecture" -> "Matching
engine: multi-attribute, multi-embedding RRF fusion":

1. Hard-constraint filtering: drop any Solution that fails to satisfy
   every `is_hard_constraint=True` RFPRequirement. (#66)
2. Per-signal scoring: attribute-match (weighted overlap, #66) plus one
   cosine-similarity score per named `embedding_space` present for the
   RFP/Solution pair (#67's `EmbeddingVector`, scored here in #68).
3. Rank (not score) each signal. (#68, `rank_signal`)
4. Fuse via weighted Reciprocal Rank Fusion. (#68, `fuse_rrf`)
5. Surfacing top-K to the buyer is the caller's job (the async job in
   `services/ai-coordinator-worker` and the read endpoint in
   `app/routers/marketplace/matches.py`), not this module's.

Deliberately has zero FastAPI/HTTP/SQLAlchemy-session/network
dependency — plain functions over plain lists of ORM model instances
(or anything duck-typed the same way) and plain floats/dicts, mirroring
`app/services/commitment_service.py` so this stays unit-testable with
in-memory objects (no DB, no fakes, no live embeddings provider needed
beyond constructing the models/vectors directly). The RRF fusion
functions in particular take already-computed scores as input (never
fetch an `EmbeddingVector` or call an embeddings client themselves) —
that fetching happens in the caller (the async job), keeping this
module a pure computation layer exactly like #66's functions already
are.
"""

import math
from dataclasses import dataclass

from app.models.marketplace.rfp import RFPRequirement
from app.models.marketplace.solution import Solution, SolutionAttribute

# Standard RRF constant (CLAUDE.md step 4: "k = 60 (the standard RRF
# constant) unless tuning says otherwise"). Module-level so callers can
# override per-invocation without editing this file, but every call site
# in this codebase currently uses the default.
DEFAULT_RRF_K = 60

# Name of the deterministic, non-ML signal produced by
# `score_attribute_match` — used as this signal's key throughout
# `signal_scores`/`signal_ranks` dicts, alongside each embedding space's
# own name (e.g. "summary", "technical_spec") as its signal key.
ATTRIBUTE_MATCH_SIGNAL = "attribute_match"


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


# --- Cosine similarity (GitHub issue #68) -----------------------------


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Plain-Python cosine similarity, no numpy dependency.

    `numpy` isn't already a dependency of `backend-api` (checked
    `pyproject.toml` before adding this) and at this scale — a handful
    of candidate Solutions per RFP, `EMBEDDING_DIMENSIONS` (1536)
    components each — a pure-Python dot-product/magnitude loop is fast
    enough that pulling in a new dependency (and its wheel-build cost in
    every service image) isn't worth it. Revisit if the candidate pool
    or dimensionality grows enough for this to become a hot path.

    Returns 0.0 (rather than raising) for a zero-magnitude vector or a
    dimension mismatch — both are data problems from a misconfigured or
    stale embedding, not something a ranking pass should crash on; the
    caller (`score_embedding_similarity`) should already prevent
    dimension mismatches by only ever comparing vectors from the same
    `embedding_space`, but this stays defensive since embeddings are
    generated across API calls/model versions that could in principle
    drift.
    """
    if len(vector_a) != len(vector_b) or not vector_a:
        return 0.0

    dot = 0.0
    mag_a = 0.0
    mag_b = 0.0
    for a, b in zip(vector_a, vector_b):
        dot += a * b
        mag_a += a * a
        mag_b += b * b

    if mag_a <= 0.0 or mag_b <= 0.0:
        return 0.0

    return dot / (math.sqrt(mag_a) * math.sqrt(mag_b))


def most_recent_vector_by_owner_and_space(
    embeddings: list,
) -> dict[tuple[str, str], list[float]]:
    """Reduces a flat list of `EmbeddingVector` rows (mixed owners,
    mixed spaces) down to one vector per `(owner_id, embedding_space)`,
    keeping only the row with the latest `generated_at` — the
    "most-recent-wins" contract already documented on
    `EmbeddingVector` (insert-only: a content edit adds a new row rather
    than updating the old one, so multiple rows can exist for the same
    owner+space and callers must pick the newest).

    Takes a flat, already-fetched list (RFP embeddings and every
    candidate Solution's embeddings mixed together) rather than two
    separate lists — the caller typically has one DB query's worth of
    rows for "this RFP and all its candidate Solutions" and doesn't need
    to separate them before calling this.
    """
    latest: dict[tuple[str, str], tuple] = {}
    for embedding in embeddings:
        key = (embedding.owner_id, embedding.embedding_space)
        current = latest.get(key)
        if current is None or embedding.generated_at > current[0]:
            latest[key] = (embedding.generated_at, embedding.vector)
    return {key: vector for key, (_, vector) in latest.items()}


# --- Rank fusion (GitHub issue #68) ------------------------------------


def rank_signal(scores: dict[str, float]) -> dict[str, int]:
    """CLAUDE.md step 3: "Rank, don't just score, each signal" — sorts
    candidate ids by `scores` descending and returns each id's 1-indexed
    rank (position), not its raw score. This is what lets RRF fuse a
    0-1 cosine similarity and a weighted attribute-overlap score without
    normalizing incompatible scales (ranks are always comparable, raw
    scores aren't).

    `scores` only contains candidates that actually have a value for
    this signal — see module docstring / `fuse_rrf`: a Solution missing
    an embedding for a given space simply isn't a key in that signal's
    `scores` dict, so it gets no rank for that signal and doesn't
    participate in it, rather than being scored 0 (which would
    incorrectly penalize it relative to a candidate that scored a real
    0.0 on that signal).

    Ties broken by candidate id ascending — arbitrary but stable, same
    "not order-dependent on dict/set iteration" reasoning as
    `rank_attribute_matches`'s tiebreak.
    """
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return {solution_id: rank for rank, (solution_id, _) in enumerate(ordered, start=1)}


@dataclass(frozen=True)
class FusedMatchResult:
    """One Solution's final fused ranking — the pure-computation
    equivalent of a `SolutionMatch` row (persistence is the caller's
    job, e.g. the async job in `services/ai-coordinator-worker`)."""

    solution_id: str
    final_rrf_score: float
    rank: int
    signal_scores: dict[str, float]
    signal_ranks: dict[str, int]


def default_signal_weights(signal_names: list[str]) -> dict[str, float]:
    """Equal weighting across whatever signals are actually present for
    this run (CLAUDE.md: "initial per-signal weights will be a guess" —
    "equal weighting across whatever signals are present for this run
    is a defensible default"). Provisional: no calibration loop exists
    yet (CLAUDE.md "RRF weight tuning" open question) — a later phase
    can replace this with weights learned from "did the buyer actually
    engage the top match" outcomes, per CLAUDE.md's explicit call-out
    that this is future work, not something to over-build now.
    """
    if not signal_names:
        return {}
    weight = 1.0 / len(signal_names)
    return {name: weight for name in signal_names}


def fuse_rrf(
    *,
    signal_scores_by_solution: dict[str, dict[str, float]],
    weights: dict[str, float] | None = None,
    k: int = DEFAULT_RRF_K,
) -> list[FusedMatchResult]:
    """CLAUDE.md step 4: weighted Reciprocal Rank Fusion across every
    signal present for this run.

    `signal_scores_by_solution`: `{solution_id: {signal_name: raw_score}}`
    — the caller has already computed the attribute-match score (#66)
    and each embedding-space cosine similarity (#67 vectors, scored via
    `cosine_similarity` above) for every candidate. A candidate missing a
    given signal (e.g. no embedding for that space) simply omits that key
    from its inner dict — see `rank_signal` docstring — rather than this
    function inventing a 0.0 for it. Pure attribute-match-only ranking
    still works correctly for a Solution with zero embeddings: it just
    never appears in any embedding signal's rank map, so its RRF score
    is computed from the attribute-match signal alone.

    `weights`: `{signal_name: weight}`. Defaults to
    `default_signal_weights` over the *union* of signal names actually
    present across all candidates (not a hardcoded signal list) — see
    that function's docstring for why equal weighting is this pass's
    default. A caller-supplied `weights` dict need not cover every
    signal; a signal missing from `weights` is treated as weight 0 (its
    rank is computed but contributes nothing to the fused score) rather
    than raising, so a caller can deliberately silence a signal without
    the fused-score formula changing shape.

    `k`: the RRF constant — `score(solution) = Σ_i weight_i · 1/(k +
    rank_i(solution))`, CLAUDE.md step 4's exact formula, k=60 unless
    overridden.

    Returns results sorted by `final_rrf_score` descending, `rank`
    populated 1-indexed on the result (this is the FUSED rank across all
    signals combined — not to be confused with any single signal's own
    per-signal rank, which lives in `signal_ranks`). Ties broken by
    `solution_id` ascending, same stable-tiebreak convention as
    `rank_attribute_matches`/`rank_signal`.

    Solutions with an entirely empty inner scores dict (no signals at
    all) still appear in the output, with `final_rrf_score = 0.0` and
    empty `signal_scores`/`signal_ranks` — CLAUDE.md: "handle Solutions
    that have zero embeddings gracefully (pure attribute-match ranking
    still applies to them)"; a Solution with literally no signals at all
    is the degenerate case of that same requirement and shouldn't raise
    or be silently dropped, just rank last.
    """
    all_signal_names: set[str] = set()
    for scores in signal_scores_by_solution.values():
        all_signal_names.update(scores.keys())

    resolved_weights = (
        default_signal_weights(sorted(all_signal_names)) if weights is None else weights
    )

    # Rank each signal independently across only the candidates that
    # have a value for it (CLAUDE.md step 3).
    ranks_by_signal: dict[str, dict[str, int]] = {}
    for signal_name in all_signal_names:
        scores_for_signal = {
            solution_id: scores[signal_name]
            for solution_id, scores in signal_scores_by_solution.items()
            if signal_name in scores
        }
        ranks_by_signal[signal_name] = rank_signal(scores_for_signal)

    results: list[FusedMatchResult] = []
    for solution_id, scores in signal_scores_by_solution.items():
        signal_ranks = {
            signal_name: ranks_by_signal[signal_name][solution_id]
            for signal_name in scores
            if solution_id in ranks_by_signal[signal_name]
        }
        fused_score = sum(
            resolved_weights.get(signal_name, 0.0) * (1.0 / (k + rank))
            for signal_name, rank in signal_ranks.items()
        )
        results.append(
            FusedMatchResult(
                solution_id=solution_id,
                final_rrf_score=fused_score,
                rank=0,  # filled in below, after sorting
                signal_scores=dict(scores),
                signal_ranks=signal_ranks,
            )
        )

    results.sort(key=lambda r: (-r.final_rrf_score, r.solution_id))
    return [
        FusedMatchResult(
            solution_id=r.solution_id,
            final_rrf_score=r.final_rrf_score,
            rank=i,
            signal_scores=r.signal_scores,
            signal_ranks=r.signal_ranks,
        )
        for i, r in enumerate(results, start=1)
    ]
