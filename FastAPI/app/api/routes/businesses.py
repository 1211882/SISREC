from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.database.session import SessionLocal
from app.models.business import Business


router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("/categories")
def list_categories(limit: int = 60):
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                "SELECT cat FROM ("
                "  SELECT unnest(string_to_array(categories, ', ')) AS cat"
                "  FROM businesses WHERE categories IS NOT NULL"
                ") t"
                " GROUP BY cat"
                " ORDER BY count(*) DESC, cat"
                " LIMIT :limit"
            ),
            {"limit": limit},
        ).fetchall()
        return sorted([row[0] for row in rows if row[0]])
    finally:
        session.close()


@router.get("")
def list_businesses(
	limit: int = Query(default=20, ge=1, le=100),
	offset: int = Query(default=0, ge=0),
	sort_by: str = Query(default="name", regex="^(name|stars|review_count)$"),
	order: str = Query(default="asc", regex="^(asc|desc)$"),
	category: str | None = Query(default=None),
	name: str | None = Query(default=None),
):
	session = SessionLocal()
	try:
		query = session.query(Business)

		if category:
			query = query.filter(Business.categories.ilike(f"%{category}%"))
		if name:
			query = query.filter(Business.name.ilike(f"%{name}%"))

		total = query.count()

		if sort_by == "stars":
			query = query.order_by(Business.stars.desc() if order == "desc" else Business.stars.asc())
		elif sort_by == "review_count":
			query = query.order_by(Business.review_count.desc() if order == "desc" else Business.review_count.asc())
		else:
			query = query.order_by(Business.name.asc())

		businesses = query.offset(offset).limit(limit).all()
		items = [
			{
				"business_id": business.business_id,
				"name": business.name,
				"city": business.city,
				"state": business.state,
				"stars": business.stars,
				"review_count": business.review_count,
				"is_open": business.is_open,
			}
			for business in businesses
		]

		page = (offset // limit) + 1 if limit else 1
		pages = ((total + limit - 1) // limit) if limit else 1

		return {
			"items": items,
			"total": total,
			"limit": limit,
			"offset": offset,
			"page": page,
			"pages": pages,
		}
	finally:
		session.close()


@router.get("/{business_id}")
def get_business_detail(business_id: str):
	session = SessionLocal()
	try:
		business = session.query(Business).filter(Business.business_id == business_id).first()
		if business is None:
			raise HTTPException(status_code=404, detail="Restaurant nao encontrado.")

		return {
			"business_id": business.business_id,
			"name": business.name,
			"address": business.address,
			"city": business.city,
			"state": business.state,
			"postal_code": business.postal_code,
			"latitude": business.latitude,
			"longitude": business.longitude,
			"stars": business.stars,
			"review_count": business.review_count,
			"is_open": business.is_open,
			"categories": business.categories,
			"attributes": business.attributes,
			"hours": business.hours,
		}
	finally:
		session.close()
