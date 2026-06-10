import math

from app.core.scoring import compute_euclidean_distance


def test_ideal_item_has_zero_distance():
    # 5 stars and the maximum review scale -> distance 0 (the ideal point).
    scale = math.log1p(1000)
    d = compute_euclidean_distance(5.0, 1000, scale)
    assert d == 0.0


def test_worst_item_has_max_distance():
    # 0 stars, 0 reviews -> farthest from the ideal (sqrt(2)).
    d = compute_euclidean_distance(0.0, 0, 1.0)
    assert math.isclose(d, math.sqrt(2.0))


def test_none_values_are_handled():
    d = compute_euclidean_distance(None, None, 1.0)
    assert math.isclose(d, math.sqrt(2.0))


def test_higher_stars_reduce_distance():
    scale = math.log1p(500)
    near = compute_euclidean_distance(4.5, 500, scale)
    far = compute_euclidean_distance(2.0, 500, scale)
    assert near < far
