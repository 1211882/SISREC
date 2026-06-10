import math

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import case, func, or_, text

from app.core.scoring import compute_euclidean_distance
from app.database.session import SessionLocal
from app.models.business import Business


router = APIRouter(prefix="/businesses", tags=["businesses"])


def build_price_range_filter(price_range: int):
	return Business.attributes["RestaurantsPriceRange2"].as_string() == str(price_range)


def extract_price_range(attributes: dict | None) -> int | None:
	if not isinstance(attributes, dict):
		return None

	raw_value = attributes.get("RestaurantsPriceRange2")
	if raw_value in (None, ""):
		return None

	try:
		price_range = int(str(raw_value).strip().strip("'\""))
	except (TypeError, ValueError):
		return None

	return price_range if 1 <= price_range <= 4 else None


def build_business_payload(business: Business, euclidean_distance: float | None = None):
	return {
		"business_id": business.business_id,
		"name": business.name,
		"city": business.city,
		"state": business.state,
		"stars": business.stars,
		"review_count": business.review_count,
		"is_open": business.is_open,
		"price_range": extract_price_range(business.attributes),
		"euclidean_distance": round(float(euclidean_distance), 6) if euclidean_distance is not None else None,
	}


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


@router.get("/by-categories")
def list_businesses_by_categories(
	categories: str = Query(min_length=1),
	price_range: int | None = Query(default=None, ge=1, le=4),
	limit: int = Query(default=12, ge=1, le=50),
):
	category_list = [category.strip() for category in categories.split(",") if category.strip()]
	if not category_list:
		return {"items": [], "categories": []}

	category_list = category_list[:3]

	session = SessionLocal()
	try:
		filters = [Business.categories.ilike(f"%{category}%") for category in category_list]
		query = session.query(Business).filter(or_(*filters))
		if price_range is not None:
			query = query.filter(build_price_range_filter(price_range))
		businesses = query.all()

		if not businesses:
			return {"items": [], "categories": category_list}

		max_review_count = max((business.review_count or 0) for business in businesses)
		max_review_scale = math.log1p(max_review_count) if max_review_count > 0 else 1.0

		ranked = [
			(
				business,
				compute_euclidean_distance(business.stars, business.review_count, max_review_scale),
			)
			for business in businesses
		]
		ranked.sort(
			key=lambda item: (
				item[1],
				-(item[0].stars or 0.0),
				-(item[0].review_count or 0),
				item[0].name or "",
			)
		)

		return {
			"items": [build_business_payload(business, distance) for business, distance in ranked[:limit]],
			"categories": category_list,
		}
	finally:
		session.close()


@router.get("")
def list_businesses(
	limit: int = Query(default=20, ge=1, le=100),
	offset: int = Query(default=0, ge=0),
	sort_by: str = Query(default="name", pattern="^(name|stars|review_count|euclidean)$"),
	order: str = Query(default="asc", pattern="^(asc|desc)$"),
	category: str | None = Query(default=None),
	name: str | None = Query(default=None),
	price_range: int | None = Query(default=None, ge=1, le=4),
	include_total: bool = Query(default=True),
):
	session = SessionLocal()
	try:
		base_query = session.query(Business)

		if category:
			base_query = base_query.filter(Business.categories.ilike(f"%{category}%"))
		if name:
			base_query = base_query.filter(Business.name.ilike(f"%{name}%"))
		if price_range is not None:
			base_query = base_query.filter(build_price_range_filter(price_range))

		total = base_query.count() if include_total else None

		if sort_by == "euclidean":
			max_review_count = base_query.with_entities(func.max(func.coalesce(Business.review_count, 0))).scalar() or 0
			max_review_scale = math.log1p(max_review_count) if max_review_count > 0 else 1.0

			stars_component = 1.0 - (func.coalesce(Business.stars, 0.0) / 5.0)
			review_scale_expr = case(
				(
					func.coalesce(Business.review_count, 0) > -1,
					func.ln(func.coalesce(Business.review_count, 0) + 1.0) / max_review_scale,
				),
				else_=0.0,
			)
			reviews_component = 1.0 - review_scale_expr
			distance_expr = func.sqrt(
				(stars_component * stars_component) + (reviews_component * reviews_component)
			).label("euclidean_distance")
			rows = (
				base_query.with_entities(Business, distance_expr)
				.order_by(
				distance_expr.asc() if order == "asc" else distance_expr.desc(),
				Business.stars.desc(),
				Business.review_count.desc(),
				Business.name.asc(),
				)
				.offset(offset)
				.limit(limit)
				.all()
			)
			items = [build_business_payload(business, distance) for business, distance in rows]
		elif sort_by == "stars":
			businesses = (
				base_query.order_by(Business.stars.desc() if order == "desc" else Business.stars.asc())
				.offset(offset)
				.limit(limit)
				.all()
			)
			items = [build_business_payload(business) for business in businesses]
		elif sort_by == "review_count":
			businesses = (
				base_query.order_by(Business.review_count.desc() if order == "desc" else Business.review_count.asc())
				.offset(offset)
				.limit(limit)
				.all()
			)
			items = [build_business_payload(business) for business in businesses]
		else:
			businesses = base_query.order_by(Business.name.asc()).offset(offset).limit(limit).all()
			items = [build_business_payload(business) for business in businesses]

		page = ((offset // limit) + 1 if limit else 1) if total is not None else None
		pages = (((total + limit - 1) // limit) if limit else 1) if total is not None else None

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
			"price_range": extract_price_range(business.attributes),
			"categories": business.categories,
			"attributes": business.attributes,
			"hours": business.hours,
		}
	finally:
		session.close()
