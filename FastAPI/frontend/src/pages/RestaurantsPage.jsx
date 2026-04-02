import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE, fetchWithTimeout } from "../utils/api";

const PAGE_SIZE = 24;

function RestaurantsPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [sortBy, setSortBy] = useState("stars");
  const [sortOrder, setSortOrder] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [categoriesError, setCategoriesError] = useState(false);

  useEffect(() => {
    async function loadCategories() {
      try {
        const response = await fetchWithTimeout(`${API_BASE}/businesses/categories`);
        if (!response.ok) {
          throw new Error("Failed to load categories.");
        }
        const data = await response.json();
        setCategories(Array.isArray(data) ? data : []);
        setCategoriesError(false);
      } catch (err) {
        console.error("Failed to load categories", err);
        setCategories([]);
        setCategoriesError(err.message || true);
      }
    }

    loadCategories();
  }, []);

  useEffect(() => {
    async function fetchBusinesses() {
      setLoading(true);
      setError("");

      try {
        const offset = (page - 1) * PAGE_SIZE;
        let url = `${API_BASE}/businesses?limit=${PAGE_SIZE}&offset=${offset}&sort_by=${sortBy}&order=${sortOrder}`;
        if (selectedCategory) {
          url += `&category=${encodeURIComponent(selectedCategory)}`;
        }
        const response = await fetchWithTimeout(url);
        if (!response.ok) {
          throw new Error("Failed to load restaurants list.");
        }

        const data = await response.json();
        if (Array.isArray(data)) {
          setItems(data);
          setTotal(data.length);
          setPages(1);
        } else {
          setItems(Array.isArray(data.items) ? data.items : []);
          setTotal(Number(data.total || 0));
          setPages(Math.max(1, Number(data.pages || 1)));
        }
      } catch (err) {
        console.error("Failed to load restaurants", err);
        setError(err.message || "Unexpected error.");
      } finally {
        setLoading(false);
      }
    }

    fetchBusinesses();
  }, [page, sortBy, sortOrder, selectedCategory]);

  function goPrevious() {
    setPage((current) => Math.max(1, current - 1));
  }

  function goNext() {
    setPage((current) => Math.min(pages, current + 1));
  }

  function changeSortOrder(event) {
    setSortOrder(event.target.value);
    setPage(1);
  }

  function changeCategory(event) {
    setSelectedCategory(event.target.value);
    setPage(1);
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
              {categories.length > 0 && (
                <label className="sort-control">
                  Category
                  <select value={selectedCategory} onChange={changeCategory}>
                    <option value="">All categories</option>
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {categoriesError && categories.length === 0 && (
                <p className="state-message error">Failed to load categories. The restaurant list is still available.</p>
              )}
              <label className="sort-control">
                Sort field
                <select value={sortBy} onChange={(e) => { setSortBy(e.target.value); setPage(1); }}>
                  <option value="stars">Rating</option>
                  <option value="review_count">Number of reviews</option>
                </select>
              </label>
              <label className="sort-control">
                Order
                <select value={sortOrder} onChange={changeSortOrder}>
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </label>
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
                    <span>{business.review_count ?? 0} reviews</span>
                    <span>{business.is_open ? "Open" : "Closed"}</span>
                  </div>
                </article>
              </Link>
            ))}
          </div>

          <div className="paging-footer">
            <button
              className="button ghost"
              type="button"
              onClick={goPrevious}
              disabled={page <= 1}
            >
              Previous
            </button>
            <span className="paging-status">Page {page} of {pages}</span>
            <button
              className="button ghost"
              type="button"
              onClick={goNext}
              disabled={page >= pages}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}

export default RestaurantsPage;
