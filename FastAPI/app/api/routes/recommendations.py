import ast
import math
from datetime import datetime
import threading
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, cast, func, or_

from app.api.deps import CurrentUser, ensure_owns_dataset_user, get_current_user
from app.core.scoring import compute_euclidean_distance
from app.database.session import SessionLocal
from app.models.auth_user_dataset_link import AuthUserDatasetLink
from app.models.auth_user_preference import AuthUserPreference
from app.models.business import Business
from app.models.review import Review
from app.models.user import User


router = APIRouter(prefix="/recommendations", tags=["recommendations"])

_MEAL_PERIOD_REFERENCE_HOUR = {
    "lunch": 13,
    "dinner": 19,
}
_WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

# Weighted-hybrid component weights (documented in the report).
_HYBRID_WEIGHT_COLLABORATIVE = 0.5
_HYBRID_WEIGHT_CONTENT = 0.2
_HYBRID_WEIGHT_PROFILE = 0.15
_HYBRID_WEIGHT_SOCIAL = 0.15

# Item cold-start: businesses with very few reviews are invisible to the
# collaborative filter (no neighbour ever rated them). We inject content-based
# candidates and give brand-new items a small exploration boost so they can
# still surface to users whose profile matches them.
_COLD_ITEM_REVIEW_THRESHOLD = 5
_COLD_ITEM_EXPLORATION_BOOST = 0.3
_CONTENT_CANDIDATE_LIMIT = 60

_RECOMMENDATION_CACHE_TTL_SECONDS = 30.0
_recommendation_cache_lock = threading.Lock()
_recommendation_cache = {
    "expires_at": 0.0,
    "ratings": None,
    "user_ratings": None,
    "item_ratings": None,
    "user_norms": None,
}


def load_ratings(limit: int | None = None):
    session = SessionLocal()
    try:
        query = (
            session.query(Review.user_id, Review.business_id, Review.stars)
            .filter(Review.stars.isnot(None))
        )
        if limit is not None:
            query = query.limit(limit)

        rows = query.all()
        return [
            {"user": user_id, "item": business_id, "rating": float(stars)}
            for user_id, business_id, stars in rows
        ]
    finally:
        session.close()


def invalidate_recommendation_cache():
    with _recommendation_cache_lock:
        _recommendation_cache["expires_at"] = 0.0
        _recommendation_cache["ratings"] = None
        _recommendation_cache["user_ratings"] = None
        _recommendation_cache["item_ratings"] = None
        _recommendation_cache["user_norms"] = None


def load_recommendation_data():
    now = time.monotonic()
    with _recommendation_cache_lock:
        if (
            _recommendation_cache["ratings"] is not None
            and _recommendation_cache["user_ratings"] is not None
            and _recommendation_cache["item_ratings"] is not None
            and _recommendation_cache["user_norms"] is not None
            and _recommendation_cache["expires_at"] > now
        ):
            return (
                _recommendation_cache["ratings"],
                _recommendation_cache["user_ratings"],
                _recommendation_cache["item_ratings"],
                _recommendation_cache["user_norms"],
            )

    ratings = load_ratings()
    user_ratings, item_ratings = build_user_item_maps(ratings)
    user_norms = compute_user_norms(user_ratings)

    with _recommendation_cache_lock:
        _recommendation_cache["ratings"] = ratings
        _recommendation_cache["user_ratings"] = user_ratings
        _recommendation_cache["item_ratings"] = item_ratings
        _recommendation_cache["user_norms"] = user_norms
        _recommendation_cache["expires_at"] = time.monotonic() + _RECOMMENDATION_CACHE_TTL_SECONDS

    return ratings, user_ratings, item_ratings, user_norms


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


def get_candidate_neighbors(user_id, target_ratings, item_ratings):
    """Only users who share at least one rated item can have non-zero cosine
    similarity. Using the item->users inverted index avoids scanning every
    user on each request (the previous behaviour was O(users) per call)."""
    neighbors = set()
    for item_id in target_ratings:
        raters = item_ratings.get(item_id)
        if raters:
            neighbors.update(raters)
    neighbors.discard(user_id)
    return neighbors


def resolve_meal_period(meal_period: str) -> str:
    if meal_period in {"lunch", "dinner"}:
        return meal_period

    current_hour = datetime.now().hour
    return "lunch" if 11 <= current_hour < 17 else "dinner"


def parse_hour_value(raw_value: str | None) -> int | None:
    if not raw_value:
        return None

    try:
        hour_text, minute_text = raw_value.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (ValueError, TypeError):
        return None

    return hour * 60 + minute


def is_open_during_reference_hour(hours: dict | None, meal_period: str) -> bool | None:
    if not isinstance(hours, dict) or meal_period not in _MEAL_PERIOD_REFERENCE_HOUR:
        return None

    reference_day = _WEEKDAY_NAMES[datetime.now().weekday()]
    reference_minutes = _MEAL_PERIOD_REFERENCE_HOUR[meal_period] * 60
    raw_schedule = hours.get(reference_day)
    if not raw_schedule:
        return None

    try:
        start_text, end_text = raw_schedule.split("-", 1)
    except ValueError:
        return None

    start_minutes = parse_hour_value(start_text)
    end_minutes = parse_hour_value(end_text)
    if start_minutes is None or end_minutes is None:
        return None

    if start_minutes == end_minutes == 0:
        return True

    if start_minutes < end_minutes:
        return start_minutes <= reference_minutes < end_minutes

    return reference_minutes >= start_minutes or reference_minutes < end_minutes


def build_meal_period_score(business_info: dict, meal_period: str) -> float:
    score = 0.0

    if not business_info:
        return score

    features = build_business_feature_set(
        business_info.get("categories"),
        business_info.get("attributes"),
    )
    if f"goodformeal:{meal_period}" in features:
        score += 1.0

    open_for_period = is_open_during_reference_hour(business_info.get("hours"), meal_period)
    if open_for_period is True:
        score += 0.5
    elif open_for_period is False:
        score -= 0.5

    if business_info.get("is_open") is False:
        score -= 0.25

    return score


def cosine_similarity(user_ratings_a, user_ratings_b, norm_a, norm_b):
    common_items = set(user_ratings_a).intersection(user_ratings_b)
    if not common_items or norm_a == 0 or norm_b == 0:
        return 0.0

    dot = sum(user_ratings_a[item] * user_ratings_b[item] for item in common_items)
    return dot / (norm_a * norm_b)


def predict_ratings_for_user(user_id, user_ratings, item_ratings, user_norms, limit=10):
    target_ratings = user_ratings.get(user_id)
    if not target_ratings:
        return []

    target_norm = user_norms.get(user_id, 0.0)
    if target_norm == 0.0:
        return []

    candidate_scores = {}
    candidate_weights = {}

    for other_user_id in get_candidate_neighbors(user_id, target_ratings, item_ratings):
        other_ratings = user_ratings.get(other_user_id)
        if not other_ratings:
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
            session.query(
                Business.business_id,
                Business.name,
                Business.city,
                Business.state,
                Business.stars,
                Business.review_count,
                Business.is_open,
                Business.categories,
                Business.attributes,
                Business.hours,
            )
            .filter(Business.business_id.in_(business_ids))
            .all()
        )
        return {
            business_id: {
                "name": name,
                "city": city,
                "state": state,
                "stars": stars,
                "review_count": review_count,
                "is_open": is_open,
                "categories": categories,
                "attributes": attributes,
                "hours": hours,
            }
            for business_id, name, city, state, stars, review_count, is_open, categories, attributes, hours in rows
        }
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
                if value_text.startswith("{") and value_text.endswith("}"):
                    try:
                        nested_value = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        nested_value = None
                    if isinstance(nested_value, dict):
                        for nested_key, nested_item in nested_value.items():
                            nested_key_text = str(nested_key).strip().lower()
                            if not nested_key_text:
                                continue
                            if nested_item is True:
                                features.add(f"{key_text}:{nested_key_text}")
                            elif isinstance(nested_item, str):
                                nested_item_text = nested_item.strip().lower()
                                if nested_item_text:
                                    features.add(f"{key_text}:{nested_key_text}:{nested_item_text}")
                            elif nested_item is not None:
                                features.add(f"{key_text}:{nested_key_text}:{str(nested_item).strip().lower()}")
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


def load_user_preferences(dataset_user_id: str) -> dict:
    """Load the auth-side preferences for a dataset user (categories, city,
    star range, friends-boost flag). Returns sensible defaults when absent."""
    default = {
        "categories": set(),
        "city": None,
        "star_min": None,
        "star_max": None,
        "use_friends_boost": True,
    }

    session = SessionLocal()
    try:
        link = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.dataset_user_id == dataset_user_id)
            .first()
        )
        if not link:
            return default

        prefs = (
            session.query(AuthUserPreference)
            .filter(AuthUserPreference.auth_user_id == link.auth_user_id)
            .first()
        )
        if not prefs:
            return default

        return {
            "categories": normalize_category_set(prefs.preferred_categories),
            "city": prefs.preferred_city.strip().lower() if prefs.preferred_city else None,
            "star_min": prefs.preferred_star_min,
            "star_max": prefs.preferred_star_max,
            "use_friends_boost": bool(prefs.use_friends_boost),
        }
    finally:
        session.close()


def load_user_friends(dataset_user_id: str) -> list[str]:
    session = SessionLocal()
    try:
        dataset_user = session.query(User).filter(User.user_id == dataset_user_id).first()
        if not dataset_user or not dataset_user.friends:
            return []
        return [fid.strip() for fid in dataset_user.friends.split(",") if fid.strip()]
    finally:
        session.close()


def compute_social_scores(candidate_ids, friend_ids, user_ratings) -> dict:
    """Social filtering: for each candidate, average the ratings given by the
    user's friends. Friends who never rated the candidate do not contribute."""
    if not friend_ids:
        return {}

    friend_rating_maps = [
        user_ratings[fid] for fid in friend_ids if fid in user_ratings
    ]
    if not friend_rating_maps:
        return {}

    social_scores = {}
    for candidate_id in candidate_ids:
        values = [
            ratings[candidate_id]
            for ratings in friend_rating_maps
            if candidate_id in ratings
        ]
        if values:
            social_scores[candidate_id] = sum(values) / len(values)
    return social_scores


def load_liked_categories(rated_ids_with_scores: dict, like_threshold: float = 4.0, max_items: int = 50) -> set[str]:
    """Categories of the items the user rated highly — used to seed content-based
    candidate retrieval for item cold-start (works even without explicit prefs)."""
    liked = [bid for bid, rating in rated_ids_with_scores.items() if rating >= like_threshold]
    if not liked:
        return set()

    session = SessionLocal()
    try:
        rows = (
            session.query(Business.categories)
            .filter(Business.business_id.in_(liked[:max_items]))
            .all()
        )
        categories: set[str] = set()
        for (raw_categories,) in rows:
            categories |= normalize_category_set(raw_categories)
        return categories
    finally:
        session.close()


def load_content_candidate_ids(
    seed_categories: set[str],
    exclude_ids: set[str],
    limit: int = _CONTENT_CANDIDATE_LIMIT,
) -> list[str]:
    """Retrieve businesses matching the user's categories, prioritising items
    with FEW reviews (cold/new items) so the collaborative filter's blind spot
    is covered. This is the item cold-start strategy."""
    if not seed_categories:
        return []

    session = SessionLocal()
    try:
        filters = [Business.categories.ilike(f"%{category}%") for category in seed_categories]
        query = session.query(Business.business_id).filter(or_(*filters))
        if exclude_ids:
            query = query.filter(Business.business_id.notin_(exclude_ids))

        # Ascending review_count gives cold/new items their chance to surface;
        # stars break ties so we still favour promising newcomers.
        rows = (
            query.order_by(
                func.coalesce(Business.review_count, 0).asc(),
                func.coalesce(Business.stars, 0.0).desc(),
            )
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows]
    finally:
        session.close()


def combine_full_hybrid_scores(
    predictions,
    target_rated_ids,
    preferences: dict,
    friend_ids: list[str],
    user_ratings: dict,
):
    """Weighted hybrid: collaborative + content + profile + social.

    Returns the candidates re-scored and sorted by the weighted combination.
    City and star-range preferences are applied later, at the endpoint, as
    soft filters with graceful fallback.
    """
    candidate_ids = [prediction["business_id"] for prediction in predictions]
    rated_ids = list(target_rated_ids)
    feature_ids = set(candidate_ids) | set(rated_ids)
    business_features = load_business_feature_sets(feature_ids)
    profile_categories = preferences.get("categories") or set()

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

    use_friends = preferences.get("use_friends_boost", True)
    social_scores = (
        compute_social_scores(candidate_ids, friend_ids, user_ratings)
        if use_friends
        else {}
    )

    hybrid = []
    for prediction in predictions:
        business_id = prediction["business_id"]
        coll_score = prediction["score"]

        content_score = 0.0
        if content_weights.get(business_id, 0.0) > 0:
            content_score = content_scores[business_id] / content_weights[business_id]

        profile_score = 0.0
        if profile_categories:
            candidate_features = business_features.get(business_id, set())
            matched = profile_categories.intersection(candidate_features)
            profile_match = len(matched) / len(profile_categories)
            profile_score = 1.0 + 4.0 * profile_match

        social_score = social_scores.get(business_id, 0.0)

        full_score = (
            _HYBRID_WEIGHT_COLLABORATIVE * coll_score
            + _HYBRID_WEIGHT_CONTENT * content_score
            + _HYBRID_WEIGHT_PROFILE * profile_score
            + _HYBRID_WEIGHT_SOCIAL * social_score
        )
        hybrid.append(
            {
                "business_id": business_id,
                "score": full_score,
                "collaborative_score": round(coll_score, 4),
                "content_score": round(content_score, 4),
                "profile_score": round(profile_score, 4),
                "social_score": round(social_score, 4),
            }
        )

    hybrid.sort(key=lambda entry: entry["score"], reverse=True)
    return hybrid


def apply_preference_filters(scored, business_info, preferences):
    """Apply star-range and city preferences as filters. Falls back to the
    unfiltered list when a filter would leave no results, so the user always
    gets recommendations."""
    star_min = preferences.get("star_min")
    star_max = preferences.get("star_max")
    preferred_city = preferences.get("city")

    filtered = scored

    if star_min is not None or star_max is not None:
        candidate = [
            entry for entry in filtered
            if _stars_in_range(business_info.get(entry["business_id"], {}).get("stars"), star_min, star_max)
        ]
        if candidate:
            filtered = candidate

    if preferred_city:
        candidate = [
            entry for entry in filtered
            if (business_info.get(entry["business_id"], {}).get("city") or "").strip().lower() == preferred_city
        ]
        if candidate:
            filtered = candidate

    return filtered


def _stars_in_range(stars, star_min, star_max) -> bool:
    if stars is None:
        return False
    if star_min is not None and stars < star_min:
        return False
    if star_max is not None and stars > star_max:
        return False
    return True


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
    meal_period: str = Query(default="auto", pattern="^(auto|lunch|dinner)$"),
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

        resolved_meal_period = resolve_meal_period(meal_period)
        payloads = []
        for business, score in results:
            business_info = {
                "business_id": business.business_id,
                "name": business.name,
                "city": business.city,
                "state": business.state,
                "categories": business.categories,
                "stars": business.stars,
                "review_count": business.review_count,
                "is_open": business.is_open,
                "attributes": business.attributes,
                "hours": business.hours,
                "ranking_score": round(float(score), 4),
            }
            business_info["meal_match_score"] = round(
                build_meal_period_score(business_info, resolved_meal_period),
                4,
            )
            business_info["meal_period"] = resolved_meal_period
            payloads.append(business_info)

        payloads.sort(
            key=lambda entry: (
                -(entry.get("meal_match_score") or 0.0),
                -(entry.get("ranking_score") or 0.0),
                -(entry.get("review_count") or 0),
                -(entry.get("stars") or 0.0),
            )
        )
        return payloads
    finally:
        session.close()


@router.get("/user/{user_id}")
def get_user_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    meal_period: str = Query(default="auto", pattern="^(auto|lunch|dinner)$"),
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_owns_dataset_user(current_user, user_id)
    _, user_ratings, item_ratings, user_norms = load_recommendation_data()

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    predictions = predict_ratings_for_user(user_id, user_ratings, item_ratings, user_norms, limit)
    business_info = load_business_info([prediction["business_id"] for prediction in predictions])
    resolved_meal_period = resolve_meal_period(meal_period)
    max_review_count = max(
        (info.get("review_count") or 0) for info in business_info.values()
    ) if business_info else 0
    max_review_scale = math.log1p(max_review_count) if max_review_count > 0 else 1.0
    max_distance = math.sqrt(2.0)

    results = []
    for prediction in predictions:
        business_id = prediction["business_id"]
        info = business_info.get(business_id, {})
        distance = compute_euclidean_distance(
            info.get("stars"),
            info.get("review_count"),
            max_review_scale,
        )
        euclidean_score = max(0.0, 5.0 * (1.0 - (distance / max_distance)))
        results.append(
            {
                "business_id": business_id,
                "name": info.get("name"),
                "city": info.get("city"),
                "state": info.get("state"),
                "stars": info.get("stars"),
                "review_count": info.get("review_count"),
                "is_open": info.get("is_open"),
                "score": round(euclidean_score, 3),
                "collaborative_score": round(prediction["score"], 3),
                "euclidean_distance": round(distance, 6),
                "meal_match_score": round(build_meal_period_score(info, resolved_meal_period), 4),
                "meal_period": resolved_meal_period,
            }
        )

    results.sort(
        key=lambda entry: (
            -(entry.get("meal_match_score") or 0.0),
            entry.get("euclidean_distance", float("inf")),
            -(entry.get("stars") or 0.0),
            -(entry.get("review_count") or 0),
            -(entry.get("score") or 0.0),
        )
    )
    return results


@router.get("/candidates/{user_id}")
def get_recommendation_candidates(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_owns_dataset_user(current_user, user_id)
    _, user_ratings, item_ratings, user_norms = load_recommendation_data()

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    predictions = predict_ratings_for_user(user_id, user_ratings, item_ratings, user_norms, limit)
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


@router.get("/hybrid/full/{user_id}")
def get_full_hybrid_recommendations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    meal_period: str = Query(default="auto", pattern="^(auto|lunch|dinner)$"),
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_owns_dataset_user(current_user, user_id)
    _, user_ratings, item_ratings, user_norms = load_recommendation_data()

    if user_id not in user_ratings:
        if dataset_user_exists(user_id):
            raise HTTPException(
                status_code=400,
                detail=f"User '{user_id}' exists in the dataset but has no ratings yet.",
            )
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    preferences = load_user_preferences(user_id)
    friend_ids = load_user_friends(user_id)
    target_rated = user_ratings[user_id]

    # Pull a larger collaborative candidate pool so the content/profile/social
    # re-ranking and the preference filters have material to work with.
    candidate_pool_size = max(limit * 5, 50)
    predictions = predict_ratings_for_user(
        user_id, user_ratings, item_ratings, user_norms, candidate_pool_size
    )
    collaborative_ids = {prediction["business_id"] for prediction in predictions}

    # Item cold-start: inject content-based candidates (matching the user's
    # preferred/liked categories), prioritising items with few reviews that the
    # collaborative filter can never reach. They enter with collaborative=0 and
    # are ranked by their content/profile/social fit.
    seed_categories = set(preferences.get("categories") or set())
    seed_categories |= load_liked_categories(target_rated)
    content_candidate_ids = load_content_candidate_ids(
        seed_categories,
        exclude_ids=set(target_rated) | collaborative_ids,
    )
    merged_predictions = list(predictions) + [
        {"business_id": business_id, "score": 0.0}
        for business_id in content_candidate_ids
        if business_id not in collaborative_ids
    ]

    hybrid_predictions = combine_full_hybrid_scores(
        merged_predictions,
        target_rated,
        preferences,
        friend_ids,
        user_ratings,
    )
    business_info = load_business_info(
        [prediction["business_id"] for prediction in hybrid_predictions]
    )

    # Exploration boost so brand-new (cold) items are not buried by popular ones.
    for prediction in hybrid_predictions:
        business_id = prediction["business_id"]
        review_count = (business_info.get(business_id, {}).get("review_count")) or 0
        is_cold = review_count < _COLD_ITEM_REVIEW_THRESHOLD
        prediction["is_cold_item"] = is_cold
        prediction["source"] = "collaborative" if business_id in collaborative_ids else "content"
        if is_cold:
            prediction["score"] += _COLD_ITEM_EXPLORATION_BOOST

    hybrid_predictions = apply_preference_filters(hybrid_predictions, business_info, preferences)
    resolved_meal_period = resolve_meal_period(meal_period)

    results = []
    for prediction in hybrid_predictions:
        info = business_info.get(prediction["business_id"], {})
        results.append(
            {
                "business_id": prediction["business_id"],
                "name": info.get("name"),
                "city": info.get("city"),
                "state": info.get("state"),
                "stars": info.get("stars"),
                "review_count": info.get("review_count"),
                "score": round(prediction["score"], 4),
                "collaborative_score": prediction.get("collaborative_score"),
                "content_score": prediction.get("content_score"),
                "profile_score": prediction.get("profile_score"),
                "social_score": prediction.get("social_score"),
                "is_cold_item": prediction.get("is_cold_item", False),
                "source": prediction.get("source", "collaborative"),
                "meal_match_score": round(build_meal_period_score(info, resolved_meal_period), 4),
                "meal_period": resolved_meal_period,
            }
        )

    results.sort(
        key=lambda entry: (
            -(entry.get("meal_match_score") or 0.0),
            -(entry.get("score") or 0.0),
        )
    )
    return results[:limit]


@router.get("/similar-users/{user_id}")
def get_similar_users(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_owns_dataset_user(current_user, user_id)
    _, user_ratings, item_ratings, user_norms = load_recommendation_data()

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
    for other_user_id in get_candidate_neighbors(user_id, target_ratings, item_ratings):
        other_ratings = user_ratings.get(other_user_id)
        if not other_ratings:
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
def predict_user_business_rating(
    user_id: str,
    business_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_owns_dataset_user(current_user, user_id)
    _, user_ratings, item_ratings, user_norms = load_recommendation_data()

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

    # Only users who rated this business can contribute to the prediction.
    for other_user_id, rating in item_ratings.get(business_id, {}).items():
        if other_user_id == user_id:
            continue

        other_ratings = user_ratings.get(other_user_id)
        if not other_ratings:
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

    neighbors.sort(key=lambda entry: entry["similarity"], reverse=True)
    return {
        "user_id": user_id,
        "business_id": business_id,
        "predicted_rating": round(weighted_sum / similarity_sum, 3),
        "weighted_sum": round(weighted_sum, 3),
        "similarity_sum": round(similarity_sum, 3),
        "neighbors": neighbors,
    }
