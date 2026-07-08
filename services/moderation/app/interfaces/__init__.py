"""Abstract ports (interfaces) for the Moderation service.

Each interface is a `typing.Protocol` — structural typing is preferred over
`abc.ABC` here because it avoids inheritance boilerplate and keeps concrete
implementations in `app/impl/` decoupled/duck-typed from these definitions.

One Protocol per file. See `app/impl/` for concrete implementations and
`app/main.py` / `app/dependencies.py` for how they're wired together via
`Depends()`.
"""
