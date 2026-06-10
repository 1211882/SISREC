import math

import pytest

from app.api.routes import recommendations as R


# ── similarity primitives ────────────────────────────────────────────────
def test_cosine_similarity_identical_users():
    a = {"i1": 5.0, "i2": 3.0}
    norm = math.sqrt(25 + 9)
    assert math.isclose(R.cosine_similarity(a, a, norm, norm), 1.0)


def test_cosine_similarity_no_common_items():
    assert R.cosine_similarity({"i1": 5.0}, {"i2": 4.0}, 5.0, 4.0) == 0.0


def test_jaccard_similarity():
    assert R.jaccard_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert R.jaccard_similarity(set(), {"a"}) == 0.0


def test_normalize_category_set():
    assert R.normalize_category_set("Pizza, Italian , ,Bars") == {"pizza", "italian", "bars"}
    assert R.normalize_category_set(None) == set()


def test_build_business_feature_set_includes_categories_and_attributes():
    feats = R.build_business_feature_set("Pizza, Bars", {"GoodForMeal": "dinner"})
    assert "pizza" in feats
    assert "goodformeal:dinner" in feats


# ── neighbour discovery + collaborative prediction ───────────────────────
def _sample_maps():
    user_ratings = {
        "A": {"i1": 5.0, "i2": 4.0},
        "B": {"i1": 5.0, "i2": 4.0, "i3": 5.0},
        "C": {"i4": 1.0},
    }
    item_ratings = {
        "i1": {"A": 5.0, "B": 5.0},
        "i2": {"A": 4.0, "B": 4.0},
        "i3": {"B": 5.0},
        "i4": {"C": 1.0},
    }
    user_norms = R.compute_user_norms(user_ratings)
    return user_ratings, item_ratings, user_norms


def test_candidate_neighbors_only_share_items():
    user_ratings, item_ratings, _ = _sample_maps()
    neighbors = R.get_candidate_neighbors("A", user_ratings["A"], item_ratings)
    assert neighbors == {"B"}  # C shares no items, A excluded


def test_predict_recommends_unrated_item_from_similar_user():
    user_ratings, item_ratings, user_norms = _sample_maps()
    preds = R.predict_ratings_for_user("A", user_ratings, item_ratings, user_norms, limit=5)
    rec_ids = {p["business_id"] for p in preds}
    assert "i3" in rec_ids  # B liked i3, A is similar to B
    assert "i1" not in rec_ids and "i2" not in rec_ids  # already rated


# ── social filtering ─────────────────────────────────────────────────────
def test_compute_social_scores_averages_friend_ratings():
    user_ratings = {"F1": {"i3": 5.0, "i9": 2.0}, "F2": {"i3": 3.0}}
    scores = R.compute_social_scores(["i3", "i5"], ["F1", "F2"], user_ratings)
    assert scores["i3"] == pytest.approx(4.0)  # (5 + 3) / 2
    assert "i5" not in scores  # no friend rated it


def test_compute_social_scores_no_friends():
    assert R.compute_social_scores(["i1"], [], {"F1": {"i1": 5.0}}) == {}


# ── preference filters ───────────────────────────────────────────────────
def test_star_range_filter_keeps_in_range():
    scored = [{"business_id": "b1", "score": 1.0}, {"business_id": "b2", "score": 2.0}]
    info = {"b1": {"stars": 4.5, "city": "x"}, "b2": {"stars": 2.0, "city": "y"}}
    prefs = {"star_min": 4.0, "star_max": 5.0, "city": None}
    out = R.apply_preference_filters(scored, info, prefs)
    assert [e["business_id"] for e in out] == ["b1"]


def test_filter_falls_back_when_empty():
    scored = [{"business_id": "b1", "score": 1.0}, {"business_id": "b2", "score": 2.0}]
    info = {"b1": {"stars": 2.0}, "b2": {"stars": 2.5}}
    prefs = {"star_min": 4.9, "star_max": 5.0, "city": None}
    out = R.apply_preference_filters(scored, info, prefs)
    assert len(out) == 2  # no item qualifies -> fallback to unfiltered


def test_city_filter():
    scored = [{"business_id": "b1", "score": 1.0}, {"business_id": "b2", "score": 2.0}]
    info = {"b1": {"city": "Philadelphia"}, "b2": {"city": "Tampa"}}
    prefs = {"star_min": None, "star_max": None, "city": "philadelphia"}
    out = R.apply_preference_filters(scored, info, prefs)
    assert [e["business_id"] for e in out] == ["b1"]


# ── weighted hybrid combination (DB call monkeypatched) ──────────────────
def test_combine_full_hybrid_scores_weighting(monkeypatch):
    monkeypatch.setattr(
        R, "load_business_feature_sets",
        lambda ids: {"r1": {"pizza", "italian"}, "c1": {"pizza"}},
    )
    predictions = [{"business_id": "c1", "score": 4.0}]
    target_rated = {"r1": 5.0}
    prefs = {"categories": {"pizza"}, "use_friends_boost": True}

    out = R.combine_full_hybrid_scores(predictions, target_rated, prefs, [], {})
    entry = out[0]

    # content: jaccard(r1,c1)=0.5 -> weighted avg rating = 5.0
    # profile: c1 matches the single profile category -> 1 + 4*1 = 5.0
    # social: no friends -> 0
    # full = 0.5*4 + 0.2*5 + 0.15*5 + 0.15*0 = 3.75
    assert entry["business_id"] == "c1"
    assert entry["content_score"] == pytest.approx(5.0)
    assert entry["profile_score"] == pytest.approx(5.0)
    assert entry["social_score"] == pytest.approx(0.0)
    assert entry["score"] == pytest.approx(3.75)


def test_combine_respects_friends_boost_flag(monkeypatch):
    monkeypatch.setattr(R, "load_business_feature_sets", lambda ids: {"c1": {"pizza"}})
    predictions = [{"business_id": "c1", "score": 0.0}]
    prefs = {"categories": set(), "use_friends_boost": False}
    user_ratings = {"F1": {"c1": 5.0}}
    out = R.combine_full_hybrid_scores(predictions, {}, prefs, ["F1"], user_ratings)
    # friends_boost disabled -> social ignored even though a friend rated c1
    assert out[0]["social_score"] == pytest.approx(0.0)
