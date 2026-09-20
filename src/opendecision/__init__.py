from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from opendecision.engine import OpenDecisionEngine


try:
    __version__ = version("OpenDecision")
except PackageNotFoundError:
    __version__ = "0+unknown"


__all__ = ["OpenDecisionEngine", "__version__"]


def __getattr__(name: str) -> Any:
    if name == "OpenDecisionEngine":
        from opendecision.engine import OpenDecisionEngine

        return OpenDecisionEngine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
