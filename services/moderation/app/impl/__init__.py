"""Concrete implementations of the ports defined in `app/interfaces/`.

One implementation per file, mirroring the interface it satisfies (e.g.
`app/impl/health.py` implements `app/interfaces/health.py`'s
`HealthCheckPort`). Implementations are wired to routes in `app/main.py`
(or `app/dependencies.py`) via provider functions passed to `Depends()` —
never imported/constructed directly inside route handler bodies.
"""
