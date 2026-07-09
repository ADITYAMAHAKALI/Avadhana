"""Database engine/session wiring and the shared declarative base.

`app/db/base.py` defines `Base`; `app/db/session.py` defines the engine,
sessionmaker, and the `get_session()` FastAPI dependency.
"""
