export const API_BASE = "http://127.0.0.1:8000";
const DEFAULT_REQUEST_TIMEOUT_MS = 30000;

export function getAuthUser() {
    try {
        return JSON.parse(localStorage.getItem("auth_user") || "null");
    } catch {
        return null;
    }
}

export function getToken() {
    return getAuthUser()?.access_token || null;
}

export function setAuthUser(user) {
    localStorage.setItem("auth_user", JSON.stringify(user));
    window.dispatchEvent(new Event("auth-changed"));
}

export function clearAuth() {
    localStorage.removeItem("auth_user");
    window.dispatchEvent(new Event("auth-changed"));
}

export async function fetchWithTimeout(url, options = {}, timeout = DEFAULT_REQUEST_TIMEOUT_MS) {
    const controller = new AbortController();
    const signal = controller.signal;
    const timer = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, { ...options, signal });
        return response;
    } catch (error) {
        if (error.name === "AbortError") {
            throw new Error("Request timed out. Please try again.");
        }
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

// Authenticated request: injects the Bearer token and, on a 401, clears the
// stale session and bounces the user to the login page.
export async function authFetch(url, options = {}, timeout = DEFAULT_REQUEST_TIMEOUT_MS) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetchWithTimeout(url, { ...options, headers }, timeout);

    if (response.status === 401) {
        clearAuth();
        if (!window.location.pathname.startsWith("/login")) {
            window.location.assign("/login");
        }
    }

    return response;
}
