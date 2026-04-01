import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function StarRating({ value }) {
  const safeValue = typeof value === "number" ? value : 0;
  const nearestHalf = Math.round(safeValue * 2) / 2;
  const fullStars = Math.floor(nearestHalf);
  const hasHalfStar = nearestHalf - fullStars === 0.5;

  return (
    <span className="star-rating" aria-label={`${safeValue} stars`}>
      {Array.from({ length: 5 }, (_, i) => {
        let style = { color: "#d7e4ec" };

        if (i < fullStars) {
          style = { color: "#f5a623" };
        } else if (i === fullStars && hasHalfStar) {
          style = {
            background: "linear-gradient(90deg, #f5a623 50%, #d7e4ec 50%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          };
        }

        return (
          <span key={i} style={style}>
            ★
          </span>
        );
      })}
    </span>
  );
}

function HomePage() {
  const isLoggedIn = Boolean(localStorage.getItem("auth_user"));
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isLoggedIn) return;

    fetch("http://127.0.0.1:8000/recommendations?limit=6")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch recommendations");
        return res.json();
      })
      .then((data) => setRecommendations(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [isLoggedIn]);

  if (isLoggedIn) {
    return (
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Welcome back</p>
          <h1>Your personalized recommendations</h1>
          <p className="lead">
            Personalized suggestions based on your profile will be available soon.
          </p>
          <Link className="button solid cta" to="/restaurants">
            Browse all restaurants
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="hero-panel">
      <div className="hero-copy">
        <p className="eyebrow">Welcome to SISREC</p>
        <h1>Top recommended restaurants</h1>
        <p className="lead">
          Discover the highest-rated places. Sign in to get personalized
          recommendations based on your preferences.
        </p>
        <Link className="button solid cta" to="/restaurants">
          View all restaurants
        </Link>
      </div>

      <div className="recommendation-grid">
        {loading && (
          <p style={{ color: "var(--muted)" }}>Loading recommendations…</p>
        )}
        {error && (
          <p style={{ color: "var(--muted)" }}>Could not load recommendations.</p>
        )}
        {!loading &&
          !error &&
          recommendations.map((item, index) => (
            <article
              key={item.business_id}
              className="recommendation-card"
              style={{ animationDelay: `${index * 80}ms` }}
            >
              <h3>
                <Link
                  to={`/restaurants/${item.business_id}`}
                  style={{ color: "inherit", textDecoration: "none" }}
                >
                  {item.name}
                </Link>
              </h3>
              <p>
                {item.city}
                {item.state ? `, ${item.state}` : ""}
              </p>
              <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
                <StarRating value={item.stars} />
                <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                  {(typeof item.stars === "number" ? item.stars.toFixed(1) : "0.0")}/5 · {item.review_count} reviews
                </span>
              </div>
            </article>
          ))}
      </div>
    </section>
  );
}

export default HomePage;
