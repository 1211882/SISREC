import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authFetch, clearAuth, getAuthUser, getToken, setAuthUser } from "./api";

describe("auth helpers", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("getAuthUser returns null when nothing is stored", () => {
    expect(getAuthUser()).toBeNull();
  });

  it("getAuthUser returns null on corrupt JSON", () => {
    localStorage.setItem("auth_user", "{not json");
    expect(getAuthUser()).toBeNull();
  });

  it("setAuthUser stores and getToken reads the token", () => {
    setAuthUser({ id: 1, access_token: "tok123" });
    expect(getToken()).toBe("tok123");
    expect(getAuthUser().id).toBe(1);
  });

  it("clearAuth removes the stored user", () => {
    setAuthUser({ id: 1, access_token: "tok" });
    clearAuth();
    expect(getAuthUser()).toBeNull();
  });
});

describe("authFetch", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("injects the Bearer token into the Authorization header", async () => {
    setAuthUser({ id: 1, access_token: "tok123" });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue({ status: 200, ok: true });

    await authFetch("http://api/test", { method: "GET" });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer tok123");
  });

  it("does not set Authorization when there is no token", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue({ status: 200, ok: true });

    await authFetch("http://api/test");

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("clears the session on a 401 response", async () => {
    setAuthUser({ id: 1, access_token: "tok" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({ status: 401, ok: false });
    // jsdom does not implement navigation; stub assign so the 401 branch runs.
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      value: { pathname: "/profile", assign },
      writable: true,
    });

    const res = await authFetch("http://api/secure");

    expect(res.status).toBe(401);
    expect(getAuthUser()).toBeNull();
    expect(assign).toHaveBeenCalledWith("/login");
  });
});
