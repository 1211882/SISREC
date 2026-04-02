from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.database.session import SessionLocal
from app.models.business import Business
from app.models.user import User
from app.models.review import Review
from app.models.auth_user_dataset_link import AuthUserDatasetLink
from app.models.auth_user_preference import AuthUserPreference
from app.api.routes.recomendations import invalidate_recommendation_cache


router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreateRequest(BaseModel):
	user_id: str = Field(min_length=1, max_length=32)
	business_id: str = Field(min_length=1, max_length=32)
	stars: float = Field(ge=1, le=5)
	text: str | None = Field(default=None, max_length=2000)
	recommend: bool | None = None


@router.get("/test-counts")
def test_counts():
	session = SessionLocal()
	try:
		return {
			"businesses": session.query(Business).count(),
			"users": session.query(User).count(),
			"reviews": session.query(Review).count(),
		}
	finally:
		session.close()


def normalize_category_list(raw: str | None) -> list[str]:
    if not raw:
        return []

    normalized = [cat.strip() for cat in raw.split(",") if cat.strip()]
    unique: list[str] = []
    for cat in normalized:
        if cat not in unique:
            unique.append(cat)
        if len(unique) >= 20:
            break
    return unique


def serialize_categories(categories: list[str] | None) -> str | None:
    if not categories:
        return None

    return ", ".join(categories)


def adjust_profile_categories_for_review(
    session,
    dataset_user_id: str,
    business_categories: str | None,
    stars: float,
    previous_stars: float | None = None,
):
    categories = normalize_category_list(business_categories)
    if not categories:
        return

    link = (
        session.query(AuthUserDatasetLink)
        .filter(AuthUserDatasetLink.dataset_user_id == dataset_user_id)
        .first()
    )
    if not link:
        return

    prefs = (
        session.query(AuthUserPreference)
        .filter(AuthUserPreference.auth_user_id == link.auth_user_id)
        .first()
    )
    current_categories = normalize_category_list(prefs.preferred_categories if prefs else None)
    updated_categories = current_categories.copy()

    add_threshold = 4.0
    remove_threshold = 2.0

    def add_categories():
        nonlocal updated_categories
        for category in categories:
            if category not in updated_categories:
                updated_categories.append(category)
            if len(updated_categories) >= 20:
                break

    def remove_categories():
        nonlocal updated_categories
        updated_categories = [cat for cat in updated_categories if cat not in categories]

    if previous_stars is not None:
        if previous_stars >= add_threshold and stars <= remove_threshold:
            remove_categories()
        elif previous_stars <= remove_threshold and stars >= add_threshold:
            add_categories()
        elif previous_stars >= add_threshold and stars >= add_threshold:
            add_categories()
        elif previous_stars <= remove_threshold and stars <= remove_threshold:
            remove_categories()
    else:
        if stars >= add_threshold:
            add_categories()
        elif stars <= remove_threshold:
            remove_categories()

    updated_categories = normalize_category_list(
        ", ".join(updated_categories)
    )

    if updated_categories != current_categories:
        categories_text = serialize_categories(updated_categories)
        if not prefs:
            prefs = AuthUserPreference(
                auth_user_id=link.auth_user_id,
                preferred_categories=categories_text,
                use_friends_boost=True,
            )
            session.add(prefs)
        else:
            prefs.preferred_categories = categories_text


@router.post("")
def create_review(payload: ReviewCreateRequest):
	session = SessionLocal()
	try:
		user = session.query(User).filter(User.user_id == payload.user_id).first()
		if not user:
			raise HTTPException(status_code=404, detail="User not found.")

		business = (
			session.query(Business)
			.filter(Business.business_id == payload.business_id)
			.first()
		)
		if not business:
			raise HTTPException(status_code=404, detail="Restaurant not found.")

		existing_review = (
			session.query(Review)
			.filter(
				Review.user_id == payload.user_id,
				Review.business_id == payload.business_id,
			)
			.first()
		)

		previous_stars = existing_review.stars if existing_review else None

		if existing_review:
			existing_review.stars = payload.stars
			existing_review.recommend = payload.recommend
			existing_review.text = payload.text
			existing_review.date = datetime.utcnow().isoformat()
			review = existing_review
			message = "Review updated successfully."
		else:
			review = Review(
				review_id=uuid4().hex[:24],
				user_id=payload.user_id,
				business_id=payload.business_id,
				stars=payload.stars,
				recommend=payload.recommend,
				text=payload.text,
				useful=0,
				funny=0,
				cool=0,
				date=datetime.utcnow().isoformat(),
			)
			session.add(review)
			message = "Review submitted successfully."

		session.commit()

		rating_stats = (
			session.query(
				func.avg(Review.stars),
				func.count(Review.review_id),
			)
			.filter(
				Review.business_id == payload.business_id,
				Review.stars.isnot(None),
			)
			.one()
		)

		business.review_count = int(rating_stats[1])
		business.stars = float(rating_stats[0]) if rating_stats[0] is not None else None
		session.commit()

		adjust_profile_categories_for_review(
			session,
			payload.user_id,
			business.categories,
			payload.stars,
			previous_stars,
		)
		session.commit()
		invalidate_recommendation_cache()

		return {
			"review_id": review.review_id,
			"user_id": review.user_id,
			"user_name": user.name,
			"business_id": review.business_id,
			"stars": review.stars,
			"review_count": business.review_count,
			"text": review.text,
			"recommend": review.recommend,
			"date": review.date,
			"message": message,
		}
	finally:
		session.close()


@router.get("/business/{business_id}")
def get_business_reviews(
	business_id: str,
	limit: int = Query(default=5, ge=1, le=50),
	offset: int = Query(default=0, ge=0),
):
	session = SessionLocal()
	try:
		business = (
			session.query(Business)
			.filter(Business.business_id == business_id)
			.first()
		)
		if not business:
			raise HTTPException(status_code=404, detail="Restaurant not found.")

		total = session.query(Review).filter(Review.business_id == business_id).count()

		reviews = (
			session.query(Review, User.name)
			.outerjoin(User, User.user_id == Review.user_id)
			.filter(Review.business_id == business_id)
			.order_by(Review.date.desc())
			.offset(offset)
			.limit(limit)
			.all()
		)

		items = [
			{
				"review_id": review.review_id,
				"user_id": review.user_id,
				"user_name": user_name or review.user_id,
				"stars": review.stars,
				"recommend": review.recommend,
				"text": review.text,
				"date": review.date,
			}
			for review, user_name in reviews
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
