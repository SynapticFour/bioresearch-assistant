"""Research Notebook / ELN API endpoints."""

import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.isolation import apply_scope, get_scope_filter, get_scope_values
from app.core.limiter import limiter
from app.models.notebook import Notebook
from app.models.paper import Paper
from app.services.llm_service import LLMServiceError, get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


# --- Request/Response schemas ---


class NotebookCreate(BaseModel):
    """Request body for POST /notebooks."""

    title: str = Field(default="", max_length=512, description="Notebook title")
    content: str = Field(
        default="",
        max_length=500_000,
        description="Markdown content (max 500KB)",
    )
    tags: list[str] = Field(default_factory=list, description="Tags")


class NotebookUpdate(BaseModel):
    """Request body for PUT /notebooks/{id}."""

    title: str | None = Field(default=None, max_length=512)
    content: str | None = Field(default=None, max_length=500_000)
    tags: list[str] | None = Field(default=None)


class NotebookLinkRequest(BaseModel):
    """Request body for POST /notebooks/{id}/link."""

    type: str = Field(..., description="paper | drs | phenopacket")
    id: str = Field(..., min_length=1, description="PMID, DRS object id, or pseudonym_id")


class AIAssistRequest(BaseModel):
    """Request body for POST /notebooks/{id}/ai-assist."""

    mode: str = Field(
        default="both",
        description="summary | next_steps | both",
    )


def _notebook_to_dict(n: Notebook) -> dict:
    """Map Notebook model to response dict."""
    return {
        "id": str(n.id),
        "title": n.title or "",
        "content": n.content or "",
        "tags": list(n.tags) if n.tags else [],
        "user_id": n.user_id,
        "team_id": n.team_id,
        "linked_pmids": list(n.linked_pmids) if n.linked_pmids else [],
        "linked_drs_ids": list(n.linked_drs_ids) if n.linked_drs_ids else [],
        "linked_phenopacket_ids": list(n.linked_phenopacket_ids)
        if n.linked_phenopacket_ids
        else [],
        "ai_summary": n.ai_summary,
        "ai_next_steps": n.ai_next_steps,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def list_notebooks(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    tag: str | None = Query(None),
) -> dict:
    """List all notebooks (paginated, optional search and tag filter)."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook)
    stmt = apply_scope(stmt, Notebook, scope)
    if search and search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.where((Notebook.title.ilike(q)) | (Notebook.content.ilike(q)))
    if tag and tag.strip():
        stmt = stmt.where(Notebook.tags.contains([tag.strip()]))
    from sqlalchemy import func

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(desc(Notebook.updated_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    notebooks = result.scalars().all()
    return {
        "items": [_notebook_to_dict(n) for n in notebooks],
        "total": total or 0,
        "skip": skip,
        "limit": limit,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_notebook(
    request: Request,
    body: NotebookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a new notebook."""
    logger.info(
        "Creating notebook for user=%s title_len=%s content_len=%s tags=%s",
        current_user.get("sub", "dev"),
        len(body.title or ""),
        len(body.content or ""),
        len(body.tags or []),
    )
    scope_vals = get_scope_values(current_user)
    nb = Notebook(
        title=(body.title or "").strip() or "Neues Notizbuch",
        content=body.content or "",
        tags=body.tags or [],
        user_id=scope_vals.get("user_id"),
        team_id=scope_vals.get("team_id"),
    )
    db.add(nb)
    await db.flush()
    await db.refresh(nb)
    return _notebook_to_dict(nb)


@router.get("/{notebook_id}", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def get_notebook(
    request: Request,
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a single notebook by ID."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook).where(Notebook.id == notebook_id)
    stmt = apply_scope(stmt, Notebook, scope)
    result = await db.execute(stmt)
    nb = result.scalar_one_or_none()
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return _notebook_to_dict(nb)


@router.put("/{notebook_id}", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def update_notebook(
    request: Request,
    notebook_id: str,
    body: NotebookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update a notebook (auto-save)."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook).where(Notebook.id == notebook_id)
    stmt = apply_scope(stmt, Notebook, scope)
    result = await db.execute(stmt)
    nb = result.scalar_one_or_none()
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if body.title is not None:
        nb.title = (body.title or "").strip() or nb.title
    if body.content is not None:
        nb.content = body.content
    if body.tags is not None:
        nb.tags = body.tags
    await db.flush()
    await db.refresh(nb)
    return _notebook_to_dict(nb)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_notebook(
    request: Request,
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Delete a notebook."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook).where(Notebook.id == notebook_id)
    stmt = apply_scope(stmt, Notebook, scope)
    result = await db.execute(stmt)
    nb = result.scalar_one_or_none()
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    await db.delete(nb)
    await db.flush()
    return None


@router.post("/{notebook_id}/ai-assist", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def notebook_ai_assist(
    request: Request,
    notebook_id: str,
    body: AIAssistRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate AI summary and/or next steps for notebook content."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook).where(Notebook.id == notebook_id)
    stmt = apply_scope(stmt, Notebook, scope)
    result = await db.execute(stmt)
    nb = result.scalar_one_or_none()
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    mode = (body.mode or "both").strip().lower()
    if mode not in ("summary", "next_steps", "both"):
        mode = "both"

    linked_context = ""
    if nb.linked_pmids:
        papers_stmt = select(Paper).where(Paper.pmid.in_(nb.linked_pmids))
        papers_stmt = apply_scope(papers_stmt, Paper, scope)
        papers_result = await db.execute(papers_stmt)
        linked_papers = papers_result.scalars().all()
        if linked_papers:
            parts = []
            for p in linked_papers[:5]:
                parts.append(f"Paper: {p.title or ''}\nAbstract: {(p.abstract or '')[:500]}")
            linked_context = "\n\n".join(parts)

    try:
        llm = get_llm_service()
        summary, next_steps = await llm.notebook_ai_assist(
            nb.content,
            mode=mode,
            linked_context=linked_context,
        )
    except LLMServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"KI-Assistent fehlgeschlagen: {e}",
        ) from e
    if summary is not None:
        nb.ai_summary = summary
    if next_steps is not None:
        nb.ai_next_steps = next_steps
    await db.flush()
    await db.refresh(nb)
    return _notebook_to_dict(nb)


@router.post("/{notebook_id}/link", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def link_resource(
    request: Request,
    notebook_id: str,
    body: NotebookLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Link a paper, DRS object, or phenopacket to the notebook."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook).where(Notebook.id == notebook_id)
    stmt = apply_scope(stmt, Notebook, scope)
    result = await db.execute(stmt)
    nb = result.scalar_one_or_none()
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    link_type = (body.type or "").strip().lower()
    link_id = (body.id or "").strip()
    if not link_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="id is required")
    if link_type == "paper":
        if link_id not in (nb.linked_pmids or []):
            nb.linked_pmids = list(nb.linked_pmids or []) + [link_id]
    elif link_type == "drs":
        if link_id not in (nb.linked_drs_ids or []):
            nb.linked_drs_ids = list(nb.linked_drs_ids or []) + [link_id]
    elif link_type == "phenopacket":
        if link_id not in (nb.linked_phenopacket_ids or []):
            nb.linked_phenopacket_ids = list(nb.linked_phenopacket_ids or []) + [link_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="type must be paper, drs, or phenopacket",
        )
    await db.flush()
    await db.refresh(nb)
    return _notebook_to_dict(nb)


@router.get("/{notebook_id}/export", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def export_notebook(
    request: Request,
    notebook_id: str,
    format: Annotated[str, Query(description="md or pdf")] = "md",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Export notebook as Markdown or PDF."""
    scope = get_scope_filter(current_user)
    stmt = select(Notebook).where(Notebook.id == notebook_id)
    stmt = apply_scope(stmt, Notebook, scope)
    result = await db.execute(stmt)
    nb = result.scalar_one_or_none()
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    fmt = (format or "md").strip().lower()
    if fmt == "md":
        content = f"# {nb.title}\n\n{nb.content or ''}"
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{nb.title or "notebook"}.md"'},
        )
    if fmt == "pdf":
        # Minimal PDF via reportlab if available; else return 501
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph((nb.title or "Notebook").replace("&", "&amp;"), styles["Title"]))
            story.append(Spacer(1, 12))
            for line in (nb.content or "").split("\n"):
                line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(line, styles["Normal"]))
            doc.build(story)
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{nb.title or "notebook"}.pdf"'
                },
            )
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    "PDF export requires reportlab. Install: pip install reportlab. "
                    "Or download as Markdown and convert locally."
                ),
            ) from None
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be md or pdf")
