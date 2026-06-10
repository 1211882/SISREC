import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import ProtectedRoute from "./ProtectedRoute";

function renderAt(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route
          path="/secret"
          element={
            <ProtectedRoute>
              <div>Secret content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("redirects to /login when not authenticated", () => {
    renderAt("/secret");
    expect(screen.getByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });

  it("redirects when a user exists but has no token", () => {
    localStorage.setItem("auth_user", JSON.stringify({ id: 1 }));
    renderAt("/secret");
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("renders children when authenticated with a token", () => {
    localStorage.setItem("auth_user", JSON.stringify({ id: 1, access_token: "tok" }));
    renderAt("/secret");
    expect(screen.getByText("Secret content")).toBeInTheDocument();
  });
});
