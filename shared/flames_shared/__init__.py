"""Shared contracts (DTOs, enums, constants) used across every Flames service.

Nothing in here talks to a database, an API, or a browser. This package is
the vocabulary modules use to hand data to each other — import from here,
never from another service's internals.
"""

__version__ = "0.1.0"
