from fastapi import APIRouter, HTTPException, Query

from app.database.session import SessionLocal
from app.models.business import Business


router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("")
def list_businesses(
	limit: int = Query(default=20, ge=1, le=100),
	offset: int = Query(default=0, ge=0),
):
	session = SessionLocal()
	try:
		total = session.query(Business).count()
		businesses = session.query(Business).offset(offset).limit(limit).all()
		items = [
			{
				"business_id": business.business_id,
				"name": business.name,
				"city": business.city,
				"state": business.state,
				"stars": business.stars,
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
