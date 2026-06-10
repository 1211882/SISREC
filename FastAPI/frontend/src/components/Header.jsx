import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { clearAuth } from "../utils/api";

function Header() {
  const [authUser, setAuthUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    function syncAuthUser() {
      const raw = localStorage.getItem("auth_user");
      if (!raw) {
        setAuthUser(null);
        return;
      }

      try {
        setAuthUser(JSON.parse(raw));
      } catch {
        setAuthUser(null);
      }
    }

    syncAuthUser();
    window.addEventListener("auth-changed", syncAuthUser);
    window.addEventListener("storage", syncAuthUser);

    return () => {
      window.removeEventListener("auth-changed", syncAuthUser);
      window.removeEventListener("storage", syncAuthUser);
    };
  }, []);

  function logout() {
    clearAuth();
    setAuthUser(null);
    navigate("/", { replace: true });
  }

  const userInitial = authUser
    ? (authUser.name || authUser.email || "U").trim()[0]?.toUpperCase() || "U"
    : null;

  return (
    <header className="topbar">
      <div className="brand-stack">
        <Link className="brand" to="/">
          SISREC
        </Link>
        <nav className="brand-links" aria-label="Main navigation">
          <Link className="brand-menu-item" to="/restaurants" title="Restaurants">
            <span className="brand-menu-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M4 10h16v10H4z" fill="currentColor" opacity="0.2" />
                <path d="M6 4h12v4H6z" fill="currentColor" />
                <path d="M4 10h16v10H4V10zm2 2v6h12v-6H6z" fill="currentColor" />
              </svg>
            </span>
            <span className="brand-menu-label">Restaurants</span>
          </Link>
          <Link className="brand-menu-item" to="/recommendations" title="Recommendations">
            <span className="brand-menu-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M12 2l2.6 5.2L20 8l-4 3.9.9 5.5L12 14.8 7.1 17.4 8 11.9 4 8l5.4-.8L12 2z" fill="currentColor" />
              </svg>
            </span>
            <span className="brand-menu-label">Recommendations</span>
          </Link>
          <Link className="brand-menu-item" to="/profile" title="Profile">
            <span className="brand-menu-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M12 12a4 4 0 100-8 4 4 0 000 8z" fill="currentColor" />
                <path d="M4 20a8 8 0 0116 0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </span>
            <span className="brand-menu-label">Profile</span>
          </Link>
        </nav>
      </div>

      <nav className="topbar-nav">
        {authUser ? (
          <>
            <Link
              className="avatar-circle"
              to="/profile"
              title={authUser.name || authUser.email}
              aria-label="Go to profile"
            >
              {userInitial}
            </Link>
            <button className="button ghost" type="button" onClick={logout}>
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link className="button ghost" to="/login">
              Login
            </Link>
            <Link className="button solid" to="/register">
              Register
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}

export default Header;
