import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { API_BASE, fetchWithTimeout } from "../utils/api";


function RecommendationsPage() {
  const navigate = useNavigate();

  const authUser = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("auth_user") || "null");
    } catch {
      return null;
    }
  }, []);

  const datasetUserId = authUser?.dataset_user_id || null;

  if (!authUser?.id) {
    navigate("/login", { replace: true });
    return null;
  }

  // ── Block 1: My recommendations ──────────────────────────────
  const [myRecs, setMyRecs] = useState([]);
  const [myRecsLoading, setMyRecsLoading] = useState(false);
  const [myRecsLoaded, setMyRecsLoaded] = useState(false);
  const [myRecsError, setMyRecsError] = useState(null);
  const [myRecsMessage, setMyRecsMessage] = useState(null);

  // ── Block 2: Similar users ────────────────────────────────────
  const [similarUsers, setSimilarUsers] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarLoaded, setSimilarLoaded] = useState(false);
  const [similarError, setSimilarError] = useState(null);

  // ── Block 3: Profile categories ──────────────────────────────
  const [profileCategories, setProfileCategories] = useState([]);
  const [profileCategoriesLoading, setProfileCategoriesLoading] = useState(false);
  const [profileCategoriesError, setProfileCategoriesError] = useState(null);
  const [categoryRestaurants, setCategoryRestaurants] = useState([]);
  const [categoryRestaurantsLoading, setCategoryRestaurantsLoading] = useState(false);
  const [categoryRestaurantsError, setCategoryRestaurantsError] = useState(null);

  // ── Block 4: Predict rating ───────────────────────────────────
  const [selectedBusinessId, setSelectedBusinessId] = useState("");
  const [businessOptions, setBusinessOptions] = useState([]);
  const [businessOptionsLoading, setBusinessOptionsLoading] = useState(false);
  const [businessOptionsError, setBusinessOptionsError] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState(null);

  async function loadMyRecommendations() {
    if (!datasetUserId) {
      setMyRecsError("No dataset user linked to this account.");
      return;
    }
    setMyRecsLoading(true);
    setMyRecsError(null);
    setMyRecsMessage(null);
    setMyRecs([]);

    try {
      const res = await fetchWithTimeout(
        `${API_BASE}/recommendations/user/${datasetUserId}?limit=10`
      );
      const data = await res.json();

      if (!res.ok) {
        const msg = data?.detail || "Failed to load recommendations.";
        if (msg.toLowerCase().includes("no ratings yet")) {
          setMyRecsMessage(
            "You don't have enough ratings yet for personalized recommendations. Showing the most popular ones instead."
          );
          const fallback = await fetchWithTimeout(`${API_BASE}/recommendations?limit=10`);
          const fallbackData = await fallback.json();
          setMyRecs(Array.isArray(fallbackData) ? fallbackData : []);
          return;
        }
        throw new Error(msg);
      }
      setMyRecs(data || []);
    } catch (err) {
      setMyRecsError(err.message || "Unexpected error.");
    } finally {
      setMyRecsLoading(false);
      setMyRecsLoaded(true);
    }
  }

  async function loadSimilarUsers() {
    if (!datasetUserId) {
      setSimilarError("No dataset user linked to this account.");
      return;
    }
    setSimilarLoading(true);
    setSimilarError(null);
    setSimilarUsers([]);

    try {
      const res = await fetchWithTimeout(
        `${API_BASE}/recommendations/similar-users/${datasetUserId}?limit=10`
      );
      const data = await res.json();

      if (!res.ok) {
        const msg = data?.detail || "Failed to load similar users.";
        if (msg.toLowerCase().includes("no ratings yet")) {
          setSimilarUsers([]);
          return;
        }
        throw new Error(msg);
      }
      setSimilarUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      setSimilarError(err.message || "Unexpected error.");
    } finally {
      setSimilarLoading(false);
      setSimilarLoaded(true);
    }
  }

  useEffect(() => {
    if (!datasetUserId) return;
    loadMyRecommendations();
  }, [datasetUserId]);

  useEffect(() => {
    if (!authUser?.id) return;

    async function loadCategoryRestaurants(categories) {
      setCategoryRestaurantsLoading(true);
      setCategoryRestaurantsError(null);
      setCategoryRestaurants([]);

      if (!categories || categories.length === 0) {
        setCategoryRestaurantsLoading(false);
        return;
      }

      try {
        const uniqueRestaurantsMap = new Map();
        const categoryRequests = categories.slice(0, 3).map((cat) =>
          fetchWithTimeout(
            `${API_BASE}/businesses?category=${encodeURIComponent(cat)}&limit=6`
          )
        );

        const responses = await Promise.all(categoryRequests);
        const results = await Promise.all(responses.map((res) => res.json()));

        results.forEach((data, index) => {
          const res = responses[index];
          if (!res.ok) return;
          const items = Array.isArray(data.items) ? data.items : [];
          items.forEach((item) => {
            if (!uniqueRestaurantsMap.has(item.business_id)) {
              uniqueRestaurantsMap.set(item.business_id, item);
            }
          });
        });

        setCategoryRestaurants(Array.from(uniqueRestaurantsMap.values()).slice(0, 12));
      } catch (err) {
        setCategoryRestaurantsError(err.message || "Unable to load restaurants for your categories.");
      } finally {
        setCategoryRestaurantsLoading(false);
      }
    }

    async function loadProfileCategories() {
      setProfileCategoriesLoading(true);
      setProfileCategoriesError(null);

      try {
        const res = await fetchWithTimeout(`${API_BASE}/auth/${authUser.id}/preferences`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Unable to load profile categories.");

        const categories = data.preferred_categories
          ? data.preferred_categories.split(",").map((cat) => cat.trim()).filter(Boolean)
          : [];
        setProfileCategories(categories);
        await loadCategoryRestaurants(categories);
      } catch (err) {
        setProfileCategoriesError(err.message || "Unable to load profile categories.");
      } finally {
        setProfileCategoriesLoading(false);
      }
    }

    loadProfileCategories();
  }, [authUser?.id]);

  useEffect(() => {
    if (!datasetUserId) return;

    async function loadBusinessOptions() {
      setBusinessOptionsLoading(true);
      setBusinessOptionsError(null);
      setBusinessOptions([]);

      try {
        const res = await fetchWithTimeout(
          `${API_BASE}/recommendations/candidates/${datasetUserId}?limit=100`
        );
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data?.detail || "Unable to load prediction candidates.");
        }

        const items = Array.isArray(data) ? data : [];
        setBusinessOptions(items.map((business) => ({
          business_id: business.business_id,
          name: business.name || business.business_id,
        })));
      } catch (err) {
        setBusinessOptionsError(err.message || "Unable to load prediction candidates.");
        setBusinessOptions([]);
      } finally {
        setBusinessOptionsLoading(false);
      }
    }

    loadBusinessOptions();
  }, [datasetUserId]);

  async function loadPrediction() {
    if (!datasetUserId) {
      setPredictionError("No dataset user linked to this account.");
      return;
    }
    if (!selectedBusinessId) {
      setPredictionError("Select a restaurant from the dropdown.");
      return;
    }

    setPredictionLoading(true);
    setPredictionError(null);
    setPrediction(null);

    try {
      const selectedBusiness = businessOptions.find((item) => item.business_id === selectedBusinessId);
      const res = await fetchWithTimeout(
        `${API_BASE}/recommendations/predict/${datasetUserId}/${encodeURIComponent(selectedBusinessId)}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to predict rating.");
      setPrediction({ ...data, business_name: selectedBusiness?.name });
    } catch (err) {
      setPredictionError(err.message || "Unexpected error.");
    } finally {
      setPredictionLoading(false);
    }
  }

  return (
    <div className="rec-page">

      {/* ── Block 1: My recommendations ── */}
      <section className="rec-block">
        <div className="rec-block-header">
          <div>
            <h2>My recommendations</h2>
            <p className="block-lead">
              Restaurants you will likely enjoy, based on users similar to you.
            </p>
          </div>
          <button
            className="button solid"
            type="button"
            onClick={loadMyRecommendations}
            disabled={myRecsLoading}
          >
            {myRecsLoading ? "Loading..." : "Load recommendations"}
          </button>
        </div>

        {myRecsMessage && <p className="info-message">{myRecsMessage}</p>}
        {myRecsError && <p className="error-message">{myRecsError}</p>}

        {!myRecsLoaded && !myRecsLoading && (
          <p className="state-message">Click "Load recommendations" to get your personalized list.</p>
        )}

        {myRecsLoaded && !myRecsLoading && !myRecsError && myRecs.length === 0 && !myRecsMessage && (
          <p className="state-message">No recommendations available at the moment.</p>
        )}

        {myRecs.length > 0 && (
          <div className="restaurant-grid" style={{ marginTop: 16 }}>
            {myRecs.map((item) => (
              <Link
                key={item.business_id}
                className="restaurant-card-link"
                to={`/restaurants/${item.business_id}`}
              >
                <article className="restaurant-card">
                  <h3>{item.name || item.business_id}</h3>
                  <p>{item.city}{item.state ? `, ${item.state}` : ""}</p>
                  <div className="card-meta">
                    <span>Score: {typeof item.score === "number" ? item.score.toFixed(3) : (item.ranking_score ?? "-")}</span>
                    {item.stars != null && <span>★ {item.stars}</span>}
                  </div>
                </article>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* ── Block 2: Predict rating ── */}
      <section className="rec-block">
        <h2>Predict rating</h2>
        <p className="block-lead">
          Select a restaurant from the list and predict the rating you would likely give it.
        </p>

        <div className="predict-form">
          <label className="sort-control" style={{ flexGrow: 1 }}>
            Restaurant
            <select
              className="text-input"
              value={selectedBusinessId}
              onChange={(e) => setSelectedBusinessId(e.target.value)}
              disabled={businessOptionsLoading}
            >
              <option value="" disabled>
                {businessOptionsLoading ? "Loading restaurants..." : "Select a restaurant..."}
              </option>
              {businessOptions.map((business) => (
                <option key={business.business_id} value={business.business_id}>
                  {business.name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button solid"
            type="button"
            onClick={loadPrediction}
            disabled={predictionLoading || businessOptionsLoading || !selectedBusinessId}
          >
            {predictionLoading ? "Predicting..." : "Predict"}
          </button>
        </div>

        {businessOptionsError && (
          <p className="error-message" style={{ marginTop: 12 }}>
            {businessOptionsError}
          </p>
        )}

        {predictionError && <p className="error-message" style={{ marginTop: 12 }}>{predictionError}</p>}

        {prediction && (
          <div className="prediction-result">
            <div className="prediction-result-header">
              <h3>
                <Link to={`/restaurants/${prediction.business_id}`} style={{ color: "inherit", textDecoration: "none" }}>
                  {prediction.business_name ?? prediction.business_id}
                </Link>
              </h3>
              {prediction.predicted_rating != null && (
                <div className="predicted-score">
                  <span className="predicted-score-value">{prediction.predicted_rating}</span>
                  <span className="predicted-score-label">/ 5</span>
                </div>
              )}
              {prediction.message && (
                <p className="state-message">{prediction.message}</p>
              )}
            </div>

            {prediction.neighbors && prediction.neighbors.length > 0 && (
              <div className="neighbors-section">
                <p className="block-lead" style={{ marginBottom: 8 }}>
                  Based on {prediction.neighbors.length} similar user{prediction.neighbors.length !== 1 ? "s" : ""}:
                </p>
                <div className="similar-user-list">
                  {prediction.neighbors.slice(0, 5).map((n) => (
                    <div key={n.user_id} className="similar-user-card">
                      <div className="similar-user-info">
                        <strong>{n.user_id}</strong>
                      </div>
                      <div className="similarity-score">
                        <div className="similarity-bar-wrap">
                          <div
                            className="similarity-bar-fill"
                            style={{ width: `${Math.round(n.similarity * 100)}%` }}
                          />
                        </div>
                        <span className="similarity-value">{Math.round(n.similarity * 100)}%</span>
                        <span className="neighbor-rating">★ {n.rating}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Block 3: Profile categories ── */}
      <section className="rec-block">
        <div className="rec-block-header">
          <div>
            <h2>My profile categories</h2>
            <p className="block-lead">
              These are the cuisine categories you selected in your profile. They help guide your personalized experience.
            </p>
          </div>
        </div>

        {profileCategoriesLoading && (
          <p className="state-message">Loading categories from your profile...</p>
        )}

        {profileCategoriesError && (
          <p className="error-message">{profileCategoriesError}</p>
        )}

        {!profileCategoriesLoading && !profileCategoriesError && profileCategories.length === 0 && (
          <p className="state-message">
            You have not selected any categories yet. Go to your profile to add categories and improve recommendations.
          </p>
        )}

        {!profileCategoriesLoading && profileCategories.length > 0 && (
          <div className="category-tags" style={{ marginTop: 12 }}>
            {profileCategories.map((cat) => (
              <span key={cat} className="category-tag">
                {cat}
              </span>
            ))}
          </div>
        )}

        {profileCategories.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h3>Restaurants based on your categories</h3>
            {categoryRestaurantsLoading && (
              <p className="state-message">Loading restaurants for your favorite categories...</p>
            )}
            {categoryRestaurantsError && (
              <p className="error-message">{categoryRestaurantsError}</p>
            )}
            {!categoryRestaurantsLoading && !categoryRestaurantsError && categoryRestaurants.length === 0 && (
              <p className="state-message">
                No restaurants were found for your current profile categories.
              </p>
            )}
            {categoryRestaurants.length > 0 && (
              <div className="restaurant-grid" style={{ marginTop: 16 }}>
                {categoryRestaurants.map((item) => (
                  <Link
                    key={item.business_id}
                    className="restaurant-card-link"
                    to={`/restaurants/${item.business_id}`}
                  >
                    <article className="restaurant-card">
                      <h3>{item.name || item.business_id}</h3>
                      <p>{item.city}{item.state ? `, ${item.state}` : ""}</p>
                      <div className="card-meta">
                        {item.stars != null && <span>★ {item.stars}</span>}
                        <span>{item.review_count != null ? `${item.review_count} reviews` : ""}</span>
                      </div>
                    </article>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Block 4: Users similar to me ── */}
      <section className="rec-block">
        <div className="rec-block-header">
          <div>
            <h2>Users similar to me</h2>
            <p className="block-lead">
              Users whose tastes are closest to yours, based on shared ratings.
            </p>
          </div>
          <button
            className="button solid"
            type="button"
            onClick={loadSimilarUsers}
            disabled={similarLoading}
          >
            {similarLoading ? "Loading..." : "Load similar users"}
          </button>
        </div>

        {similarError && <p className="error-message">{similarError}</p>}

        {!similarLoaded && !similarLoading && (
          <p className="state-message">Click "Load similar users" to see who has similar tastes.</p>
        )}

        {similarLoaded && !similarLoading && !similarError && similarUsers.length === 0 && (
          <p className="state-message">
            No similar users found. Rate more restaurants to improve results.
          </p>
        )}

        {similarUsers.length > 0 && (
          <div className="similar-user-list" style={{ marginTop: 16 }}>
            {similarUsers.map((user, index) => (
              <div key={user.user_id} className="similar-user-card">
                <div className="similar-user-rank">#{index + 1}</div>
                <div className="similar-user-info">
                  <strong>{user.name || "Unknown"}</strong>
                  <span className="similar-user-meta">{user.review_count} reviews</span>
                </div>
                <div className="similarity-score">
                  <div className="similarity-bar-wrap">
                    <div
                      className="similarity-bar-fill"
                      style={{ width: `${Math.round(user.similarity * 100)}%` }}
                    />
                  </div>
                  <span className="similarity-value">
                    {Math.round(user.similarity * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default RecommendationsPage;
