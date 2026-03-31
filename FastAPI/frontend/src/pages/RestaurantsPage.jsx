import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";
const PAGE_SIZE = 24;

function RestaurantsPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchBusinesses() {
      setLoading(true);
      setError("");

      try {
        const offset = (page - 1) * PAGE_SIZE;
        const response = await fetch(`${API_BASE}/businesses?limit=${PAGE_SIZE}&offset=${offset}`);
        if (!response.ok) {
          throw new Error("Failed to load restaurants list.");
        }

        const data = await response.json();
        if (Array.isArray(data)) {
          // Compatibilidade com formato antigo da API.
          setItems(data);
          setTotal(data.length);
          setPages(1);
        } else {
          setItems(Array.isArray(data.items) ? data.items : []);
          setTotal(Number(data.total || 0));
          setPages(Math.max(1, Number(data.pages || 1)));
        }
      } catch (err) {
        setError(err.message || "Unexpected error.");
      } finally {
        setLoading(false);
      }
    }

    fetchBusinesses();
  }, [page]);

  function goPrevious() {
    setPage((current) => Math.max(1, current - 1));
  }

  function goNext() {
    setPage((current) => Math.min(pages, current + 1));
  }

  return (
    <section className="list-panel">
      <div className="list-header">
        <h1>Restaurants List</h1>
        <p>Results loaded from the businesses table.</p>
      </div>

      {loading && <p className="state-message">Loading restaurants...</p>}
      {error && <p className="state-message error">{error}</p>}

      {!loading && !error && (
        <>
          <div className="paging-toolbar">
            <p className="state-message">
              Total: {total} restaurants | Page {page} of {pages}
            </p>
            <div className="paging-actions">
              <button
                className="button ghost"
                type="button"
                onClick={goPrevious}
                disabled={page <= 1}
              >
                Previous
              </button>
              <button
                className="button ghost"
                type="button"
                onClick={goNext}
                disabled={page >= pages}
              >
                Next
              </button>
            </div>
          </div>

          <div className="restaurant-grid">
            {items.map((business) => (
              <Link
                key={business.business_id}
                className="restaurant-card-link"
                to={`/restaurants/${business.business_id}`}
              >
              <article className="restaurant-card">
                <h3>{business.name || "No name"}</h3>
                <p>
                  {(business.city || "City n/a") + ", " + (business.state || "State n/a")}
                </p>
                <div className="card-meta">
                  <span>Stars: {business.stars ?? "-"}</span>
                  <span>{business.is_open ? "Open" : "Closed"}</span>
                </div>
              </article>
              </Link>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default RestaurantsPage;
