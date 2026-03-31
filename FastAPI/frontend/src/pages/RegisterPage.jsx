import { useState } from "react";
import { Link } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";

function RegisterPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Unable to register.");
      }

      setSuccess(payload.message || "Account created successfully.");
      setFormData({ name: "", email: "", password: "" });
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
          Initial registration form. Data persistence is already integrated
          with the backend.
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

        <button className="button solid" type="submit" disabled={loading}>
          {loading ? "Creating account..." : "Create account"}
        </button>

        {error && <p className="form-message error">{error}</p>}
        {success && <p className="form-message success">{success}</p>}

        <p className="auth-footnote">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </form>
    </section>
  );
}

export default RegisterPage;
