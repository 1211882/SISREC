import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { API_BASE, fetchWithTimeout, setAuthUser } from "../utils/api";

const MAX_SURVEY_CATEGORIES = 20;

function RegisterPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });

  // Cold-start survey (optional): seeds the user profile at registration.
  const [availableCategories, setAvailableCategories] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [categoryToAdd, setCategoryToAdd] = useState("");
  const [preferredCity, setPreferredCity] = useState("");
  const [priceRange, setPriceRange] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadCategories() {
      try {
        const res = await fetchWithTimeout(`${API_BASE}/businesses/categories`);
        const data = await res.json();
        if (res.ok && Array.isArray(data)) {
          setAvailableCategories(data);
        }
      } catch {
        // categories are optional for registration
      }
    }
    loadCategories();
  }, []);

  function addCategory() {
    if (!categoryToAdd || selectedCategories.includes(categoryToAdd)) return;
    if (selectedCategories.length >= MAX_SURVEY_CATEGORIES) return;
    setSelectedCategories([...selectedCategories, categoryToAdd]);
    setCategoryToAdd("");
  }

  function removeCategory(cat) {
    setSelectedCategories(selectedCategories.filter((c) => c !== cat));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const body = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
        preferred_categories:
          selectedCategories.length > 0 ? selectedCategories.join(", ") : null,
        preferred_city: preferredCity.trim() || null,
        preferred_price_range: priceRange ? Number(priceRange) : null,
      };

      const response = await fetchWithTimeout(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Unable to register.");
      }

      // Auto-login: the register response already carries the access token.
      setAuthUser(payload);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Unexpected registration error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-panel">
      <div className="auth-copy">
        <p className="eyebrow">New user</p>
        <h1>Create account</h1>
        <p>
          Only email and password are required. The short survey below helps us
          build your profile and avoid the cold-start problem — you can change it
          later in your profile.
        </p>
      </div>

      <form className="auth-form" onSubmit={onSubmit}>
        <label>
          Name
          <input
            type="text"
            placeholder="Your name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </label>

        <label>
          Email
          <input
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            placeholder="Minimum 8 characters"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
            minLength={8}
          />
        </label>

        <fieldset className="survey-fieldset" style={{ border: "1px solid var(--border, #d7e4ec)", borderRadius: 10, padding: 16 }}>
          <legend>Cold-start survey (optional)</legend>

          <label>
            Favorite cuisine categories
            <div className="category-add-row" style={{ display: "flex", gap: 8 }}>
              <select
                value={categoryToAdd}
                onChange={(e) => setCategoryToAdd(e.target.value)}
                disabled={selectedCategories.length >= MAX_SURVEY_CATEGORIES}
              >
                <option value="">Select a category to add...</option>
                {availableCategories
                  .filter((cat) => !selectedCategories.includes(cat))
                  .map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
              </select>
              <button
                type="button"
                className="button solid"
                onClick={addCategory}
                disabled={!categoryToAdd || selectedCategories.length >= MAX_SURVEY_CATEGORIES}
              >
                Add
              </button>
            </div>
          </label>

          {selectedCategories.length > 0 && (
            <div className="category-tags" style={{ marginTop: 10 }}>
              {selectedCategories.map((cat) => (
                <span key={cat} className="category-tag">
                  {cat}
                  <button
                    type="button"
                    onClick={() => removeCategory(cat)}
                    aria-label={`Remove ${cat}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          <label style={{ marginTop: 12 }}>
            Preferred city
            <input
              type="text"
              placeholder="e.g. Philadelphia"
              value={preferredCity}
              onChange={(e) => setPreferredCity(e.target.value)}
            />
          </label>

          <label style={{ marginTop: 12 }}>
            Preferred price range
            <select value={priceRange} onChange={(e) => setPriceRange(e.target.value)}>
              <option value="">No preference</option>
              <option value="1">$ - Budget</option>
              <option value="2">$$ - Moderate</option>
              <option value="3">$$$ - Expensive</option>
              <option value="4">$$$$ - Premium</option>
            </select>
          </label>
        </fieldset>

        <button className="button solid" type="submit" disabled={loading}>
          {loading ? "Creating account..." : "Create account"}
        </button>

        {error && <p className="form-message error">{error}</p>}

        <p className="auth-footnote">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </form>
    </section>
  );
}

export default RegisterPage;
