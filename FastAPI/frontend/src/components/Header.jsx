import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

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
    localStorage.removeItem("auth_user");
    setAuthUser(null);
    window.dispatchEvent(new Event("auth-changed"));
    navigate("/");
  }

  const userInitial = authUser
    ? (authUser.name || authUser.email || "U").trim()[0]?.toUpperCase() || "U"
    : null;

  return (
    <header className="topbar">
      <Link className="brand" to="/">
        SISREC
      </Link>

      <nav className="topbar-nav">
        <Link className="nav-button ghost" to="/restaurants">
          Restaurants
        </Link>
        {authUser && (
          <Link className="nav-button ghost" to="/recommendations">
            Recommendations
          </Link>
        )}
        {authUser ? (
          <>
            <Link className="nav-button ghost" to="/profile">
              Profile
            </Link>
            <span className="avatar-circle" title={authUser.name || authUser.email}>
              {userInitial}
            </span>
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
