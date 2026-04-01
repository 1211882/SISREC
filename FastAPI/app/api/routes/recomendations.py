from fastapi import APIRouter, Query
from sqlalchemy import Float, cast, func

from app.database.session import SessionLocal
from app.models.business import Business


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    min_reviews_weight: int = Query(default=50, ge=1, le=1000),
):
    """
    Non-personalized recommender using Bayesian weighted rating:
    score = (v/(v+m))*R + (m/(v+m))*C

    Where:
    - v: business review_count
    - R: business stars
    - C: global average stars
    - m: min_reviews_weight (confidence threshold)
    """
    session = SessionLocal()
    try:
        global_avg_stars = (
            session.query(func.avg(Business.stars))
            .filter(Business.stars.isnot(None))
            .scalar()
        )
        if global_avg_stars is None:
            global_avg_stars = 0.0

        m = float(min_reviews_weight)
        v = cast(func.coalesce(Business.review_count, 0), Float)
        r = func.coalesce(Business.stars, global_avg_stars)

        ranking_score = (
            (v / (v + m)) * r
            + (m / (v + m)) * float(global_avg_stars)
        ).label("ranking_score")

        results = (
            session.query(
                Business,
                ranking_score,
            )
            .filter(Business.stars.isnot(None))
            .order_by(
                ranking_score.desc(),
                Business.review_count.desc(),
                Business.stars.desc(),
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "business_id": business.business_id,
                "name": business.name,
                "city": business.city,
                "state": business.state,
                "categories": business.categories,
                "stars": business.stars,
                "review_count": business.review_count,
                "ranking_score": round(float(score), 4),
            }
            for business, score in results
        ]
    finally:
        session.close()
