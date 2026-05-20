from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import get_current_user
from database import get_db
from models import Lead, LeadActivity, LeadStatus
from schemas import LeadActivityRead, LeadCreate, LeadListResponse, LeadRead, LeadStatusUpdate

router = APIRouter(prefix="/leads", tags=["Leads"], dependencies=[Depends(get_current_user)])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    normalized_email = _normalize_email(payload.email)

    existing_lead = db.execute(select(Lead).where(Lead.email == normalized_email)).scalar_one_or_none()
    if existing_lead is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A lead with this email already exists.")

    lead = Lead(
        name=payload.name,
        email=normalized_email,
        company=payload.company,
        phone=payload.phone,
        source=payload.source,
        status=payload.status,
    )

    db.add(lead)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A lead with this email already exists.")

    db.refresh(lead)
    return lead


@router.get("", response_model=LeadListResponse)
def list_leads(
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Lead)
    if status_filter is not None:
        stmt = stmt.where(Lead.status == status_filter)
    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Lead.name.ilike(search_term),
                Lead.email.ilike(search_term),
                Lead.company.ilike(search_term),
            )
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    results = (
        db.execute(
            stmt.order_by(Lead.id.asc()).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": results,
    }


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    return lead


@router.get("/{lead_id}/activity", response_model=list[LeadActivityRead])
def get_lead_activity(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    stmt = select(LeadActivity).where(LeadActivity.lead_id == lead_id).order_by(LeadActivity.changed_at.asc(), LeadActivity.id.asc())
    return db.execute(stmt).scalars().all()


@router.patch("/{lead_id}/status", response_model=LeadRead)
def update_lead_status(lead_id: int, payload: LeadStatusUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    lead.status = payload.status
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to update lead status.")

    db.refresh(lead)
    return lead
