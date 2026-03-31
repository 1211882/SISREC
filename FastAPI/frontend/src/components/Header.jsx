import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

function Header() {
  const [authUser, setAuthUser] = useState(null);

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
  }

  return (
    <header className="topbar">
      <Link className="brand" to="/">
        SISREC
      </Link>

      <nav className="topbar-nav">
        <Link className="text-link" to="/restaurants">
          Restaurants
        </Link>
        {authUser ? (
          <>
            <Link className="text-link" to="/profile">
              Profile
            </Link>
            <span className="user-pill">Signed in: {authUser.name || authUser.email}</span>
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
