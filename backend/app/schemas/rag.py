"""Pydantic schemas for RAG (Frag deine Bibliothek) API."""

from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    """Request body for POST /library/rag."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natürlichsprachige Frage",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Anzahl Papers als Kontext",
    )
    language: str = Field(
        default="de",
        description="Antwortsprache: de | en",
    )


class RAGSource(BaseModel):
    """One paper used as source for the RAG answer."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Paper title")
    similarity_score: float = Field(..., description="Similarity score (0-100)")
    used_chars: int = Field(..., description="Wie viel vom Abstract verwendet (Zeichen)")


class RAGResponse(BaseModel):
    """Response for POST /library/rag."""

    answer: str = Field(..., description="LLM-generated answer")
    sources: list[RAGSource] = Field(default_factory=list, description="Verwendete Papers")
    question: str = Field(..., description="Eingabefrage")
    model_used: str = Field(..., description="z.B. mistral oder claude")
    context_papers: int = Field(..., description="Anzahl Papers als Kontext verwendet")
