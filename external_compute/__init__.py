"""External compute providers, normalized to MIOSA's Computer surface."""

from .provider import (
    ComputeProvider,
    ComputerInfo,
    ExecResult,
    ExternalComputer,
    ShellEndpoint,
)
from .orgo_provider import OrgoComputer, OrgoProvider

__all__ = [
    "ComputeProvider",
    "ComputerInfo",
    "ExecResult",
    "ExternalComputer",
    "ShellEndpoint",
    "OrgoProvider",
    "OrgoComputer",
]

# MiosaProvider is optional — only importable if the `miosa` SDK is installed.
try:  # pragma: no cover
    from .miosa_provider import MiosaComputer, MiosaProvider  # noqa: F401

    __all__ += ["MiosaProvider", "MiosaComputer"]
except Exception:  # pragma: no cover
    pass
