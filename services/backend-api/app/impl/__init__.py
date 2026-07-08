"""Concrete implementations of the interfaces in `app.interfaces`.

One file per implementation, named after the interface it implements
(e.g. `app/impl/health.py` implements `app.interfaces.health.HealthCheckPort`).
These classes are never imported directly into route handler bodies —
route handlers depend on the interface type, wired up via provider
functions (see `app/main.py`).
"""
