from datetime import datetime
from threading import Lock
from typing import Dict, Any

from cachetools import TTLCache
from fastapi import APIRouter, Depends
from sqlalchemy import func, desc, extract
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Invoice, User
from schemas import (
    AnalyticsResponse, ItcSummaryResponse,
    MonthlySpend, MonthlyCount, SupplierSpend,
    ItcCurrentMonth, SupplierItc,
)

router = APIRouter(prefix="/api", tags=["analytics"])

# ── Item 25: TTL cache keyed by company_id (5-minute TTL) ────────────
_analytics_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
_itc_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
_cache_lock = Lock()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        return AnalyticsResponse(
            total_invoices=0, total_spend=0, total_tax=0,
            monthly_spend=[], top_suppliers=[], monthly_invoice_count=[],
        )

    company_id = str(current_user.company_id)

    with _cache_lock:
        if company_id in _analytics_cache:
            return _analytics_cache[company_id]

    result = _build_analytics(db, current_user.company_id)

    with _cache_lock:
        _analytics_cache[company_id] = result

    return result


def _build_analytics(db: Session, company_id) -> AnalyticsResponse:
    base = db.query(Invoice).filter(
        Invoice.company_id == company_id,
        Invoice.status == "SUCCESS",
    )

    totals = base.with_entities(
        func.count(Invoice.id).label("count"),
        func.sum(Invoice.total).label("spend"),
        # Item 15: COALESCE prevents NULL when any tax column is NULL
        func.sum(
            func.coalesce(Invoice.cgst, 0)
            + func.coalesce(Invoice.sgst, 0)
            + func.coalesce(Invoice.igst, 0)
        ).label("tax"),
    ).first()

    # Item 16: use column references instead of string literals for group_by
    year_col = extract("year", Invoice.created_at).label("year")
    month_col = extract("month", Invoice.created_at).label("month")

    monthly_data = base.with_entities(
        year_col,
        month_col,
        func.count(Invoice.id).label("count"),
        func.sum(Invoice.total).label("total"),
        func.sum(
            func.coalesce(Invoice.cgst, 0)
            + func.coalesce(Invoice.sgst, 0)
            + func.coalesce(Invoice.igst, 0)
        ).label("tax"),
    ).group_by(year_col, month_col).order_by(year_col, month_col).all()

    monthly_spend = []
    monthly_invoice_count = []
    for row in monthly_data:
        m_str = f"{int(row.year)}-{int(row.month):02d}"
        monthly_spend.append(MonthlySpend(month=m_str, total=row.total or 0, tax=row.tax or 0))
        monthly_invoice_count.append(MonthlyCount(month=m_str, count=row.count or 0))

    suppliers = (
        base.with_entities(
            Invoice.seller_name,
            func.sum(Invoice.total).label("total_spend"),
        )
        .filter(Invoice.seller_name.isnot(None))
        .group_by(Invoice.seller_name)
        .order_by(desc("total_spend"))
        .limit(5)
        .all()
    )
    top_suppliers = [
        SupplierSpend(name=s.seller_name, total_spend=s.total_spend or 0)
        for s in suppliers
    ]

    return AnalyticsResponse(
        total_invoices=totals.count or 0 if totals else 0,
        total_spend=totals.spend or 0 if totals else 0,
        total_tax=totals.tax or 0 if totals else 0,
        monthly_spend=monthly_spend,
        top_suppliers=top_suppliers,
        monthly_invoice_count=monthly_invoice_count,
    )


@router.get("/itc-summary", response_model=ItcSummaryResponse)
async def get_itc_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        return ItcSummaryResponse(
            current_month=ItcCurrentMonth(total_itc=0),
            percentage_change=0,
            disclaimer="",
            supplier_breakdown=[],
        )

    company_id = str(current_user.company_id)

    with _cache_lock:
        if company_id in _itc_cache:
            return _itc_cache[company_id]

    result = _build_itc_summary(db, current_user.company_id)

    with _cache_lock:
        _itc_cache[company_id] = result

    return result


def _build_itc_summary(db: Session, company_id) -> ItcSummaryResponse:
    now = datetime.utcnow()

    def _tax_sum(year: int, month: int) -> float:
        return db.query(
            func.sum(
                func.coalesce(Invoice.cgst, 0)
                + func.coalesce(Invoice.sgst, 0)
                + func.coalesce(Invoice.igst, 0)
            )
        ).filter(
            Invoice.company_id == company_id,
            Invoice.status == "SUCCESS",
            extract("year", Invoice.created_at) == year,
            extract("month", Invoice.created_at) == month,
        ).scalar() or 0

    curr_month = _tax_sum(now.year, now.month)
    prev_month_num = now.month - 1 if now.month > 1 else 12
    prev_year_num = now.year if now.month > 1 else now.year - 1
    prev_month = _tax_sum(prev_year_num, prev_month_num)

    if prev_month > 0:
        pct_change = round(((curr_month - prev_month) / prev_month) * 100, 1)
    elif curr_month > 0:
        pct_change = 100.0
    else:
        pct_change = 0.0

    suppliers = db.query(
        Invoice.seller_name,
        Invoice.seller_gstin,
        func.sum(func.coalesce(Invoice.cgst, 0)).label("cgst"),
        func.sum(func.coalesce(Invoice.sgst, 0)).label("sgst"),
        func.sum(func.coalesce(Invoice.igst, 0)).label("igst"),
        func.sum(
            func.coalesce(Invoice.cgst, 0)
            + func.coalesce(Invoice.sgst, 0)
            + func.coalesce(Invoice.igst, 0)
        ).label("total_itc"),
    ).filter(
        Invoice.company_id == company_id,
        Invoice.status == "SUCCESS",
        extract("year", Invoice.created_at) == now.year,
        extract("month", Invoice.created_at) == now.month,
        Invoice.seller_name.isnot(None),
    ).group_by(Invoice.seller_name, Invoice.seller_gstin).all()

    supplier_breakdown = [
        SupplierItc(
            seller_name=s.seller_name,
            seller_gstin=s.seller_gstin or "UNKNOWN",
            cgst=s.cgst or 0,
            sgst=s.sgst or 0,
            igst=s.igst or 0,
            total_itc=s.total_itc or 0,
        )
        for s in suppliers
    ]

    return ItcSummaryResponse(
        current_month=ItcCurrentMonth(total_itc=curr_month),
        percentage_change=pct_change,
        disclaimer="ITC estimates based on current scans and successfully processed invoices.",
        supplier_breakdown=supplier_breakdown,
    )
