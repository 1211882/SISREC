import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

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
        const response = await fetch(`${API_BASE}/businesses/${businessId}`);
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
              <h3>Location</h3>
              <ul>
                <li>Latitude: {item.latitude ?? "-"}</li>
                <li>Longitude: {item.longitude ?? "-"}</li>
                <li>City: {item.city || "-"}</li>
                <li>State: {item.state || "-"}</li>
              </ul>
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
