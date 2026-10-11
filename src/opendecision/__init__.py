from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from opendecision.engine import OpenDecisionEngine
    from opendecision.images import ImageDecisionEngine


try:
    __version__ = version("OpenDecision")
except PackageNotFoundError:
    __version__ = "0+unknown"


__all__ = ["OpenDecisionEngine", "ImageDecisionEngine", "__version__"]


def __getattr__(name: str) -> Any:
    if name == "ImageDecisionEngine":
        from opendecision.images import ImageDecisionEngine

        return ImageDecisionEngine
    if name == "OpenDecisionEngine":
        from opendecision.engine import OpenDecisionEngine

        return OpenDecisionEngine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
