import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";

function ProfilePage() {
  const authUser = useMemo(() => {
    const raw = localStorage.getItem("auth_user");
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }, []);

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [nameInput, setNameInput] = useState("");
  const [friendInput, setFriendInput] = useState("");

  const [savingName, setSavingName] = useState(false);
  const [savingFriend, setSavingFriend] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  async function loadProfile() {
    if (!authUser?.id) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/auth/${authUser.id}/social-profile`);
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Unable to load profile.");
      }

      setProfile(payload);
      setNameInput(payload.auth_name || "");
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authUser?.id]);

  if (!authUser?.id) {
    return (
      <section className="list-panel">
        <h1>Profile</h1>
        <p className="state-message">You need to log in to manage your profile.</p>
        <Link className="button solid" to="/login">
          Go to login
        </Link>
      </section>
    );
  }

  async function saveName(event) {
    event.preventDefault();
    setSavingName(true);
    setError("");
    setSuccessMessage("");

    try {
      const response = await fetch(`${API_BASE}/auth/${authUser.id}/name`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: nameInput.trim() }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Unable to update name.");
      }

      const updatedAuthUser = {
        ...authUser,
        name: payload.name,
      };
      localStorage.setItem("auth_user", JSON.stringify(updatedAuthUser));
      window.dispatchEvent(new Event("auth-changed"));

      setSuccessMessage(payload.message || "Name updated successfully.");
      await loadProfile();
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setSavingName(false);
    }
  }

  async function addFriend(event) {
    event.preventDefault();
    setSavingFriend(true);
    setError("");
    setSuccessMessage("");

    try {
      const response = await fetch(`${API_BASE}/auth/${authUser.id}/friends`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ friend_user_id: friendInput.trim() }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Unable to add friend.");
      }

      setFriendInput("");
      setSuccessMessage(payload.message || "Friend added successfully.");
      await loadProfile();
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setSavingFriend(false);
    }
  }

  async function removeFriend(friendUserId) {
    setSavingFriend(true);
    setError("");
    setSuccessMessage("");

    try {
      const response = await fetch(`${API_BASE}/auth/${authUser.id}/friends/${friendUserId}`, {
        method: "DELETE",
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Unable to remove friend.");
      }

      setSuccessMessage(payload.message || "Friend removed successfully.");
      await loadProfile();
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setSavingFriend(false);
    }
  }

  return (
    <section className="profile-panel">
      <div className="profile-header">
        <h1>User profile</h1>
        <p>
          Here you can update your name, manage friends, and track how many
          reviews your mapped dataset user has made.
        </p>
      </div>

      {loading && <p className="state-message">Loading profile...</p>}
      {error && <p className="form-message error">{error}</p>}
      {successMessage && <p className="form-message success">{successMessage}</p>}

      {profile && (
        <>
          <div className="profile-cards">
            <article className="restaurant-card">
              <h3>Authenticated account</h3>
              <p>Name: {profile.auth_name || "-"}</p>
              <p>Email: {authUser.email || "-"}</p>
            </article>

            <article className="restaurant-card">
              <h3>Dataset account</h3>
              <p>user_id: {profile.dataset_user_id || "Not linked"}</p>
              <p>Dataset name: {profile.dataset_name || "-"}</p>
              <p>Reviews made: {profile.reviews_count ?? 0}</p>
            </article>

            <article className="restaurant-card">
              <h3>Friends</h3>
              <p>Total friends: {profile.friends?.length || 0}</p>
            </article>
          </div>

          <div className="profile-forms">
            <form className="auth-form" onSubmit={saveName}>
              <h3>Change name</h3>
              <label>
                New name
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  required
                />
              </label>
              <button className="button solid" type="submit" disabled={savingName}>
                {savingName ? "Saving..." : "Save name"}
              </button>
            </form>

            <form className="auth-form" onSubmit={addFriend}>
              <h3>Add friend</h3>
              <label>
                friend_user_id
                <input
                  type="text"
                  value={friendInput}
                  onChange={(e) => setFriendInput(e.target.value)}
                  required
                />
              </label>
              <button className="button solid" type="submit" disabled={savingFriend}>
                {savingFriend ? "Adding..." : "Add"}
              </button>
            </form>
          </div>

          <section className="friends-section">
            <h3>Friends list</h3>
            {profile.friends && profile.friends.length > 0 ? (
              <ul className="friend-list">
                {profile.friends.map((friend) => (
                  <li key={friend.user_id} className="friend-item">
                    <div>
                      <strong>{friend.name || "Name unavailable"}</strong>
                      <p>{friend.user_id}</p>
                    </div>
                    <button
                      className="button ghost"
                      type="button"
                      onClick={() => removeFriend(friend.user_id)}
                      disabled={savingFriend}
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="state-message">You do not have linked friends yet.</p>
            )}
          </section>
        </>
      )}
    </section>
  );
}

export default ProfilePage;
