import { useState } from "react";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { API_BASE, fetchWithTimeout } from "../utils/api";


function LoginPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetchWithTimeout(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Unable to log in.");
      }

      localStorage.setItem("auth_user", JSON.stringify(payload));
      window.dispatchEvent(new Event("auth-changed"));
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Unexpected login error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-panel">
      <div className="auth-copy">
        <p className="eyebrow">Access</p>
        <h1>Log in to the platform</h1>
        <p>
          Enter your credentials to sign in. Your session is stored in
          the browser for the next personalization steps.
        </p>
      </div>

      <form className="auth-form" onSubmit={onSubmit}>
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
            placeholder="********"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
            minLength={8}
          />
        </label>

        <button className="button solid" type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>

        {error && <p className="form-message error">{error}</p>}

        <p className="auth-footnote">
          Don't have an account yet? <Link to="/register">Register</Link>
        </p>
      </form>
    </section>
  );
}

export default LoginPage;
