import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import AuthGuard from "@/components/AuthGuard";
import { server } from "@/test/msw/server";

// Next.js router mock is in setup.ts, but let's spy on useRouter
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

describe("AuthGuard", () => {
  it("renders children when explicitly authenticated", () => {
    render(
      <AuthGuard isAuthenticated={true}>
        <div data-testid="protected-content">Secret Dashboard</div>
      </AuthGuard>,
    );

    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("redirects and shows fallback when unauthenticated", () => {
    render(
      <AuthGuard isAuthenticated={false} loginPath="/login">
        <div data-testid="protected-content">Secret Dashboard</div>
      </AuthGuard>,
    );

    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(mockReplace).toHaveBeenCalledWith("/login");
    expect(screen.getByRole("alert")).toHaveTextContent("Redirecting to login…");
  });

  it("shows custom fallback while loading", () => {
    render(
      <AuthGuard
        isLoading={true}
        fallback={<div data-testid="custom-spinner">Checking credentials...</div>}
      >
        <div data-testid="protected-content">Secret Dashboard</div>
      </AuthGuard>,
    );

    expect(screen.getByTestId("custom-spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("verifies identity automatically against MSW /me endpoint and renders children on success", async () => {
    render(
      <AuthGuard>
        <div data-testid="protected-content">Identity Confirmed</div>
      </AuthGuard>,
    );

    // Initial state is loading
    expect(screen.getByRole("status")).toBeInTheDocument();

    // After MSW resolves mockIdentityResponse
    await waitFor(() => {
      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });
  });

  it("redirects to login when MSW /me returns 401 Unauthorized", async () => {
    server.use(
      http.get("*/me", () => {
        return new HttpResponse(null, { status: 401 });
      }),
    );

    render(
      <AuthGuard loginPath="/auth/login">
        <div data-testid="protected-content">Never Shown</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/auth/login");
    });
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("uses custom checkAuth function when provided", async () => {
    const mockCheckAuth = vi.fn().mockResolvedValue(false);

    render(
      <AuthGuard checkAuth={mockCheckAuth} loginPath="/custom-login">
        <div>Content</div>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockCheckAuth).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith("/custom-login");
    });
  });
});
