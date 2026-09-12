"""Developer-facing inspection tools for compiled FlyDSL kernels."""

__all__ = ["analyze_isa"]


def __getattr__(name):
    # Keep ``python -m flydsl.tools.isa_analyzer`` free of runpy's
    # already-imported-module warning while retaining the convenient API.
    if name == "analyze_isa":
        from .isa_analyzer import analyze_isa

        return analyze_isa
    raise AttributeError(name)
