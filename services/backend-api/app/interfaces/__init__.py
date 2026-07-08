"""Abstract ports (interfaces) for the backend API service.

Each interface is defined as a `typing.Protocol` (PEP 544, structural
typing) rather than an `abc.ABC` subclass. This avoids inheritance
boilerplate for concrete implementations and keeps them duck-typed and
decoupled from the interface module. One file per interface.
"""
