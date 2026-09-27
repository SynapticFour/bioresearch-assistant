"""Optional juxtaposition of a Locus RAG answer and Ferrum technical metadata.

Active only when Locus and both Ferrum DRS and WES URLs are configured.
Inactive configurations return an empty summary and do not raise.
"""

from modules.variant_interpretation.summary import (
    DISCLAIMER,
    InterpretationSummary,
    is_active,
    summarize,
)

__all__ = [
    "DISCLAIMER",
    "InterpretationSummary",
    "is_active",
    "summarize",
]
