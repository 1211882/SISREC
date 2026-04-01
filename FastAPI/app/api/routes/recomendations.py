import math
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Float, cast, func

from app.database.session import SessionLocal
from app.models.auth_user_dataset_link import AuthUserDatasetLink
from app.models.auth_user_preference import AuthUserPreference
from app.models.business import Business
from app.models.review import Review
from app.models.user import User


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def load_ratings(limit: int = 20000):
    session = SessionLocal()
    try:
        rows = (
            session.query(Review.user_id, Review.business_id, Review.stars)
            .filter(Review.stars.isnot(None))
            .limit(limit)
            .all()
        )
        return [
            {"user": user_id, "item": business_id, "rating": float(stars)}
            for user_id, business_id, stars in rows
        ]
    finally:
        session.close()


def build_user_item_maps(ratings):
    user_ratings = {}
    item_ratings = {}

    for rating in ratings:
        user_ratings.setdefault(rating["user"], {})[rating["item"]] = rating["rating"]
        item_ratings.setdefault(rating["item"], {})[rating["user"]] = rating["rating"]

    return user_ratings, item_ratings


def compute_user_norms(user_ratings):
    return {
        user_id: math.sqrt(sum(value * value for value in ratings.values()))
        for user_id, ratings in user_ratings.items()
    }


def cosine_similarity(user_ratings_a, user_ratings_b, norm_a, norm_b):
    common_items = set(user_ratings_a).intersection(user_ratings_b)
    if not common_items or norm_a == 0 or norm_b == 0:
        return 0.0

    dot = sum(user_ratings_a[item] * user_ratings_b[item] for item in common_items)
    return dot / (norm_a * norm_b)


def predict_ratings_for_user(user_id, user_ratings, user_norms, limit=10):
    target_ratings = user_ratings.get(user_id)
    if not target_ratings:
        return []

    target_norm = user_norms.get(user_id, 0.0)
    if target_norm == 0.0:
        return []

    candidate_scores = {}
    candidate_weights = {}

    for other_user_id, other_ratings in user_ratings.items():
        if other_user_id == user_id:
            continue

        other_norm = user_norms.get(other_user_id, 0.0)
        similarity = cosine_similarity(target_ratings, other_ratings, target_norm, other_norm)
        if similarity <= 0:
            continue

        for business_id, rating in other_ratings.items():
            if business_id in target_ratings:
                continue
            candidate_scores[business_id] = candidate_scores.get(business_id, 0.0) + similarity * rating
            candidate_weights[business_id] = candidate_weights.get(business_id, 0.0) + similarity

    predictions = [
        {"business_id": business_id, "score": score / candidate_weights[business_id]}
        for business_id, score in candidate_scores.items()
        if candidate_weights.get(business_id, 0.0) > 0
    ]

    predictions.sort(key=lambda entry: entry["score"], reverse=True)
    return predictions[:limit]


def load_business_info(business_ids):
    session = SessionLocal()
    try:
        rows = (
            session.query(Business.business_id, Business.name, Business.city, Business.state)
            .filter(Business.business_id.in_(business_ids))
            .all()
        )
        return {business_id: {"name": name, "city": city, "state": state} for business_id, name, city, state in rows}
    finally:
        session.close()


def normalize_category_set(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {cat.strip().lower() for cat in raw.split(",") if cat.strip()}


def build_business_feature_set(categories: str | None, attributes: dict | None) -> set[str]:
    features = normalize_category_set(categories)
    if isinstance(attributes, dict):
        for key, value in attributes.items():
            key_text = str(key).strip().lower()
            if key_text:
                features.add(key_text)
            if isinstance(value, str):
                value_text = value.strip().lower()
                if value_text:
                    features.add(f"{key_text}:{value_text}")
            elif value is not None:
                features.add(str(value).strip().lower())
    return features


def load_business_feature_sets(business_ids):
    session = SessionLocal()
    try:
        rows = (
            session.query(Business.business_id, Business.categories, Business.attributes)
            .filter(Business.business_id.in_(business_ids))
            .all()
        )
        return {
            business_id: build_business_feature_set(categories, attributes)
            for business_id, categories, attributes in rows
        }
    finally:
        session.close()


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return float(len(intersection)) / float(len(union)) if union else 0.0


def load_user_profile_categories(dataset_user_id: str) -> set[str]:
    session = SessionLocal()
    try:
        link = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.dataset_user_id == dataset_user_id)
            .first()
        )
        if not link:
            return set()

        prefs = (
            session.query(AuthUserPreference)
            .filter(AuthUserPreference.auth_user_id == link.auth_user_id)
            .first()
        )
        return normalize_category_set(prefs.preferred_categories if prefs else None)
    finally:
        session.close()


def combine_content_and_collaborative_scores(predictions, user_ratings, target_rated_ids):
    candidate_ids = [prediction["business_id"] for prediction in predictions]
    rated_ids = list(target_rated_ids)
    feature_ids = set(candidate_ids) | set(rated_ids)
    business_features = load_business_feature_sets(feature_ids)

    content_scores = {}
    content_weights = {}

    for rated_business_id in rated_ids:
        rated_features = business_features.get(rated_business_id)
        if not rated_features:
            continue
        rating = target_rated_ids[rated_business_id]
        for candidate_id in candidate_ids:
            if candidate_id == rated_business_id:
                continue
            candidate_features = business_features.get(candidate_id)
            if not candidate_features:
                continue
            similarity = jaccard_similarity(rated_features, candidate_features)
            if similarity <= 0:
                continue
            content_scores[candidate_id] = content_scores.get(candidate_id, 0.0) + similarity * rating
            content_weights[candidate_id] = content_weights.get(candidate_id, 0.0) + similarity

    hybrid = []
    for prediction in predictions:
        business_id = prediction["business_id"]
        coll_score = prediction["score"]
        content_score = 0.0
        if content_weights.get(business_id, 0.0) > 0:
            content_score = content_scores[business_id] / content_weights[business_id]
        hybrid_score = (0.7 * coll_score) + (0.3 * content_score)
        hybrid.append({"business_id": business_id, "score": hybrid_score})

    hybrid.sort(key=lambda entry: entry["score"], reverse=True)
    return hybrid


def combine_profile_and_collaborative_scores(predictions, profile_categories: set[str]):
    hybrid = []
    for prediction in predictions:
        business_id = prediction["business_id"]
        coll_score = prediction["score"]
        profile_score = 0.0
        if profile_categories:
            business_features = load_business_feature_sets([business_id]).get(business_id, set())
            matched = profile_categories.intersection(business_features)
            profile_match = len(matched) / len(profile_categories)
            profile_score = 1.0 + 4.0 * profile_match
        hybrid_score = (0.7 * coll_score) + (0.3 * profile_score)
        hybrid.append({"business_id": business_id, "score": hybrid_score})

    hybrid.sort(key=lambda entry: entry["score"], reverse=True)
    return hybrid


def dataset_user_exists(user_id: str) -> bool:
    session = SessionLocal()
    try:
        return session.query(User).filter(User.user_id == user_id).first() is not None
    finally:
        session.close()


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


@router.get("/user/{user_id}")
def get_user_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    ratings = load_ratings()
    user_ratings, _ = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    predictions = predict_ratings_for_user(user_id, user_ratings, user_norms, limit)
    business_info = load_business_info([prediction["business_id"] for prediction in predictions])

    return [
        {
            "business_id": prediction["business_id"],
            "name": business_info.get(prediction["business_id"], {}).get("name"),
            "city": business_info.get(prediction["business_id"], {}).get("city"),
            "state": business_info.get(prediction["business_id"], {}).get("state"),
            "score": prediction["score"],
        }
        for prediction in predictions
    ]


@router.get("/candidates/{user_id}")
def get_recommendation_candidates(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=200),
):
    ratings = load_ratings()
    user_ratings, _ = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    predictions = predict_ratings_for_user(user_id, user_ratings, user_norms, limit)
    business_info = load_business_info([prediction["business_id"] for prediction in predictions])

    return [
        {
            "business_id": prediction["business_id"],
            "name": business_info.get(prediction["business_id"], {}).get("name"),
            "city": business_info.get(prediction["business_id"], {}).get("city"),
            "state": business_info.get(prediction["business_id"], {}).get("state"),
            "score": prediction["score"],
        }
        for prediction in predictions
    ]


@router.get("/hybrid/content/{user_id}")
def get_content_hybrid_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    ratings = load_ratings()
    user_ratings, _ = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    predictions = predict_ratings_for_user(user_id, user_ratings, user_norms, limit)
    hybrid_predictions = combine_content_and_collaborative_scores(
        predictions,
        user_ratings,
        user_ratings[user_id],
    )
    business_info = load_business_info([prediction["business_id"] for prediction in hybrid_predictions])

    return [
        {
            "business_id": prediction["business_id"],
            "name": business_info.get(prediction["business_id"], {}).get("name"),
            "city": business_info.get(prediction["business_id"], {}).get("city"),
            "state": business_info.get(prediction["business_id"], {}).get("state"),
            "score": prediction["score"],
        }
        for prediction in hybrid_predictions
    ]


@router.get("/hybrid/profile/{user_id}")
def get_profile_hybrid_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    ratings = load_ratings()
    user_ratings, _ = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    profile_categories = load_user_profile_categories(user_id)
    predictions = predict_ratings_for_user(user_id, user_ratings, user_norms, limit)
    hybrid_predictions = combine_profile_and_collaborative_scores(
        predictions,
        profile_categories,
    )
    business_info = load_business_info([prediction["business_id"] for prediction in hybrid_predictions])

    return [
        {
            "business_id": prediction["business_id"],
            "name": business_info.get(prediction["business_id"], {}).get("name"),
            "city": business_info.get(prediction["business_id"], {}).get("city"),
            "state": business_info.get(prediction["business_id"], {}).get("state"),
            "score": prediction["score"],
        }
        for prediction in hybrid_predictions
    ]


@router.get("/similar-users/{user_id}")
def get_similar_users(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    ratings = load_ratings()
    user_ratings, _ = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    target_ratings = user_ratings[user_id]
    target_norm = user_norms.get(user_id, 0.0)

    similar = []
    for other_user_id, other_ratings in user_ratings.items():
        if other_user_id == user_id:
            continue
        other_norm = user_norms.get(other_user_id, 0.0)
        sim = cosine_similarity(target_ratings, other_ratings, target_norm, other_norm)
        if sim > 0:
            similar.append({"user_id": other_user_id, "similarity": round(sim, 4)})

    similar.sort(key=lambda x: x["similarity"], reverse=True)
    top = similar[:limit]

    if not top:
        return []

    similar_ids = [u["user_id"] for u in top]
    session = SessionLocal()
    try:
        user_rows = (
            session.query(User.user_id, User.name)
            .filter(User.user_id.in_(similar_ids))
            .all()
        )
        name_map = {uid: name for uid, name in user_rows}

        review_rows = (
            session.query(Review.user_id, func.count(Review.stars))
            .filter(Review.user_id.in_(similar_ids))
            .group_by(Review.user_id)
            .all()
        )
        review_map = {uid: cnt for uid, cnt in review_rows}
    finally:
        session.close()

    return [
        {
            "user_id": u["user_id"],
            "name": name_map.get(u["user_id"], "Unknown"),
            "similarity": u["similarity"],
            "review_count": review_map.get(u["user_id"], 0),
        }
        for u in top
    ]


@router.get("/predict/{user_id}/{business_id}")
def predict_user_business_rating(user_id: str, business_id: str):
    ratings = load_ratings()
    user_ratings, _ = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    current_rating = user_ratings[user_id].get(business_id)
    if current_rating is not None:
        return {
            "user_id": user_id,
            "business_id": business_id,
            "message": "User already rated this business",
            "rating": current_rating,
        }

    target_ratings = user_ratings[user_id]
    target_norm = user_norms.get(user_id, 0.0)
    if target_norm == 0.0:
        return {
            "user_id": user_id,
            "business_id": business_id,
            "message": "No similar users with ratings for this business",
        }

    weighted_sum = 0.0
    similarity_sum = 0.0
    neighbors = []

    for other_user_id, other_ratings in user_ratings.items():
        if other_user_id == user_id:
            continue

        rating = other_ratings.get(business_id)
        if rating is None:
            continue

        other_norm = user_norms.get(other_user_id, 0.0)
        similarity = cosine_similarity(target_ratings, other_ratings, target_norm, other_norm)
        if similarity <= 0:
            continue

        weighted_sum += similarity * rating
        similarity_sum += similarity
        neighbors.append(
            {
                "user_id": other_user_id,
                "similarity": round(similarity, 4),
                "rating": round(rating, 3),
            }
        )

    if similarity_sum == 0.0:
        return {
            "user_id": user_id,
            "business_id": business_id,
            "message": "No similar users with ratings for this business",
        }

    return {
        "user_id": user_id,
        "business_id": business_id,
        "predicted_rating": round(weighted_sum / similarity_sum, 3),
        "weighted_sum": round(weighted_sum, 3),
        "similarity_sum": round(similarity_sum, 3),
        "neighbors": neighbors,
    }
