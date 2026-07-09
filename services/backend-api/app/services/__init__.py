"""Business logic layer.

This is where the platform's non-negotiable constraints (3-slot limit,
90-day commitment lock, commitment-gated voice) are enforced — not in
route handlers, not in the ORM layer. Every service here takes repo
*ports* (see `app.interfaces`) as constructor/function dependencies, so
each one is unit-testable against fake in-memory repos with no real
database required (see `tests/unit/`).
"""
