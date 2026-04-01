import { Link, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { API_BASE, fetchWithTimeout } from "../utils/api";


function isTruthyAttribute(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    return ["true", "1", "yes", "y"].includes(normalized);
  }
  return false;
}

function formatAttributeKey(key) {
  return key
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .trim();
}

const WEEK_ORDER = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

function formatDayLabel(dayKey) {
  const labels = {
    Monday: "Monday",
    Tuesday: "Tuesday",
    Wednesday: "Wednesday",
    Thursday: "Thursday",
    Friday: "Friday",
    Saturday: "Saturday",
    Sunday: "Sunday",
  };
  return labels[dayKey] || dayKey;
}

function normalizeHourToken(token) {
  const [hours, minutes] = String(token).split(":");
  const h = String(Number(hours)).padStart(2, "0");
  const m = String(Number(minutes)).padStart(2, "0");
  return `${h}:${m}`;
}

function formatHourRange(rawRange) {
  if (typeof rawRange !== "string" || !rawRange.includes("-")) {
    return "Closed";
  }

  const [start, end] = rawRange.split("-");
  const normalized = `${normalizeHourToken(start)} - ${normalizeHourToken(end)}`;
  if (normalized === "00:00 - 00:00") {
    return "Closed";
  }
  return normalized;
}

function RestaurantDetailPage() {
  const { businessId } = useParams();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rating, setRating] = useState(5);
  const [recommend, setRecommend] = useState(true);
  const [comment, setComment] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitMessage, setSubmitMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [reviews, setReviews] = useState([]);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [reviewsError, setReviewsError] = useState("");

  const authUser = useMemo(() => {
    const raw = localStorage.getItem("auth_user");
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }, []);

  const datasetUserId = authUser?.dataset_user_id || null;
  const activeAttributes = item?.attributes && typeof item.attributes === "object"
    ? Object.entries(item.attributes)
      .filter(([, value]) => isTruthyAttribute(value))
      .map(([key]) => formatAttributeKey(key))
    : [];

  const categoryList = typeof item?.categories === "string"
    ? item.categories
      .split(",")
      .map((category) => category.trim())
      .filter(Boolean)
    : [];

  const hoursEntries = item?.hours && typeof item.hours === "object"
    ? WEEK_ORDER.map((day) => ({
      day,
      value: formatHourRange(item.hours?.[day]),
    }))
    : [];

  useEffect(() => {
    async function fetchDetail() {
      setLoading(true);
      setError("");

      try {
        const response = await fetchWithTimeout(`${API_BASE}/businesses/${businessId}`);
        if (!response.ok) {
          throw new Error("Unable to load restaurant details.");
        }
        const data = await response.json();
        setItem(data);
      } catch (err) {
        setError(err.message || "Unexpected error.");
      } finally {
        setLoading(false);
      }
    }

    if (businessId) {
      fetchDetail();
    }
  }, [businessId]);

  useEffect(() => {
    async function fetchReviews() {
      if (!businessId) return;
      setReviewsLoading(true);
      setReviewsError("");

      try {
        const response = await fetchWithTimeout(`${API_BASE}/reviews/business/${businessId}?limit=20`);
        if (!response.ok) {
          throw new Error("Unable to load reviews.");
        }
        const data = await response.json();
        setReviews(Array.isArray(data) ? data : []);
      } catch (err) {
        setReviewsError(err.message || "Unexpected error.");
      } finally {
        setReviewsLoading(false);
      }
    }

    fetchReviews();
  }, [businessId]);

  async function submitReview() {
    if (!datasetUserId) {
      setSubmitError("You must be logged in to submit a review.");
      return;
    }

    setSubmitError("");
    setSubmitMessage("");
    setSubmitting(true);

    try {
      const response = await fetchWithTimeout(`${API_BASE}/reviews`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: datasetUserId,
          business_id: businessId,
          stars: rating,
          text: comment.trim() || null,
          recommend,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to submit review.");
      }

      setSubmitMessage(data.message || "Review submitted successfully.");
      setComment("");
      setRating(5);
      setRecommend(true);

      if (item) {
        setItem({
          ...item,
          review_count: data.review_count ?? item.review_count,
          stars: data.stars ?? item.stars,
        });
      }
      setReviews((current) => [
        {
          review_id: data.review_id,
          user_id: data.user_id,
          stars: data.stars,
          recommend: data.recommend,
          text: data.text,
          date: data.date,
        },
        ...current,
      ]);
    } catch (err) {
      setSubmitError(err.message || "Unexpected error.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="detail-panel">
      <div className="detail-top">
        <Link className="button ghost" to="/restaurants">
          Back to list
        </Link>
      </div>

      {loading && <p className="state-message">Loading details...</p>}
      {error && <p className="state-message error">{error}</p>}

      {!loading && !error && item && (
        <>
          <header className="detail-header">
            <h1>{item.name || "No name"}</h1>
            <p>
              {(item.address || "Address n/a") + " | "}
              {(item.city || "City n/a") + ", "}
              {(item.state || "State n/a") + " "}
              {item.postal_code || ""}
            </p>
          </header>

          <div className="detail-grid">
            <article className="detail-card">
              <h3>General information</h3>
              <ul>
                <li>Stars: {item.stars ?? "-"}</li>
                <li>Total reviews: {item.review_count ?? "-"}</li>
                <li>Status: {item.is_open ? "Open" : "Closed"}</li>
              </ul>
            </article>

            <article className="detail-card">
              <h3>Leave a review</h3>
              {datasetUserId ? (
                <div className="review-form">
                  <label>
                    Rating
                    <select
                      value={rating}
                      onChange={(event) => setRating(Number(event.target.value))}
                    >
                      {[5, 4, 3, 2, 1].map((value) => (
                        <option key={value} value={value}>
                          {value} star{value > 1 ? "s" : ""}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={recommend}
                      onChange={(event) => setRecommend(event.target.checked)}
                    />
                    Recommend this restaurant?
                  </label>

                  <label>
                    Review
                    <textarea
                      rows={4}
                      value={comment}
                      onChange={(event) => setComment(event.target.value)}
                      placeholder="Write a short comment (optional)"
                    />
                  </label>

                  <button
                    className="button solid"
                    type="button"
                    onClick={submitReview}
                    disabled={submitting}
                  >
                    {submitting ? "Submitting..." : "Submit review"}
                  </button>

                  {submitError && <p className="form-message error">{submitError}</p>}
                  {submitMessage && <p className="form-message success">{submitMessage}</p>}
                </div>
              ) : (
                <p>Please log in to submit a review and recommend this restaurant.</p>
              )}
            </article>

            <article className="detail-card">
              <h3>Location</h3>
              <ul>
                <li>Latitude: {item.latitude ?? "-"}</li>
                <li>Longitude: {item.longitude ?? "-"}</li>
                <li>City: {item.city || "-"}</li>
                <li>State: {item.state || "-"}</li>
              </ul>
            </article>

            <article className="detail-card detail-span">
              <h3>Recent reviews</h3>
              {reviewsLoading ? (
                <p className="state-message">Loading reviews...</p>
              ) : reviewsError ? (
                <p className="state-message error">{reviewsError}</p>
              ) : reviews.length === 0 ? (
                <p>No reviews yet. Be the first to add one.</p>
              ) : (
                <div className="review-list">
                  {reviews.map((review) => (
                    <div key={review.review_id} className="review-card">
                      <div className="review-card-header">
                        <strong>{review.user_id}</strong>
                        <span>{review.stars ?? "-"} ★</span>
                      </div>
                      <p>{review.text || "No comment provided."}</p>
                      <div className="review-card-meta">
                        <span>{review.recommend ? "Recommended" : "Not recommended"}</span>
                        <span>{review.date ? new Date(review.date).toLocaleDateString() : ""}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>

            <article className="detail-card detail-span">
              <h3>Categories</h3>
              {categoryList.length > 0 ? (
                <div className="attribute-chips">
                  {categoryList.map((category) => (
                    <span key={category} className="attribute-chip">
                      {category}
                    </span>
                  ))}
                </div>
              ) : (
                <p>No categories.</p>
              )}
            </article>

            <article className="detail-card detail-span">
              <h3>Attributes</h3>
              {activeAttributes.length > 0 ? (
                <div className="attribute-chips">
                  {activeAttributes.map((attribute) => (
                    <span key={attribute} className="attribute-chip">
                      {attribute}
                    </span>
                  ))}
                </div>
              ) : (
                <p>No active attributes.</p>
              )}
            </article>

            <article className="detail-card detail-span">
              <h3>Schedule</h3>
              {hoursEntries.length > 0 ? (
                <div className="hours-grid">
                  {hoursEntries.map((entry) => {
                    const isClosed = entry.value === "Closed";
                    return (
                      <div
                        key={entry.day}
                        className={`hours-card ${isClosed ? "closed" : "open"}`}
                      >
                        <p className="hours-day">{formatDayLabel(entry.day)}</p>
                        <p className="hours-time">{entry.value}</p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p>No schedule.</p>
              )}
            </article>
          </div>
        </>
      )}
    </section>
  );
}

export default RestaurantDetailPage;
