import math


def compute_euclidean_distance(
    stars: float | None,
    review_count: int | None,
    max_review_scale: float,
) -> float:
    """Distance to the ideal item (5 stars, most-reviewed) in normalized space.

    Lower is better. Stars are normalized to [0, 1]; review counts are
    log-scaled and normalized by ``max_review_scale``.
    """
    normalized_stars = (stars or 0.0) / 5.0
    normalized_reviews = (
        math.log1p(review_count or 0) / max_review_scale if max_review_scale > 0 else 0.0
    )
    return math.sqrt((1.0 - normalized_stars) ** 2 + (1.0 - normalized_reviews) ** 2)
