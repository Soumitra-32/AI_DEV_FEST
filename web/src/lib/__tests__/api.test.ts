import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import {
  ApiError,
  BASE_URL,
  DEMO_TOKEN,
  buildApiUrl,
  fetchAnomalies,
  fetchCreditReadiness,
  fetchExplain,
  fetchForecast,
  fetchHealth,
  fetchIdentity,
  fetchMetrics,
  fetchParseGoal,
  fetchSavingsPlan,
  request,
} from "@/lib/api";
import { server } from "@/test/msw/server";

describe("api.ts client", () => {
  describe("URL building and trailing-slash normalization", () => {
    it("normalizes base URLs without trailing slash", () => {
      expect(buildApiUrl("/forecast", "http://localhost:8000")).toBe(
        "http://localhost:8000/forecast",
      );
    });

    it("normalizes base URLs with trailing slashes", () => {
      expect(buildApiUrl("/forecast", "http://localhost:8000/")).toBe(
        "http://localhost:8000/forecast",
      );
      expect(buildApiUrl("/forecast", "http://localhost:8000///")).toBe(
        "http://localhost:8000/forecast",
      );
    });

    it("handles paths missing leading slash", () => {
      expect(buildApiUrl("forecast", "http://localhost:8000")).toBe(
        "http://localhost:8000/forecast",
      );
    });

    it("defaults to BASE_URL when base is omitted", () => {
      const expected = `${BASE_URL.replace(/\/+$/, "")}/health`;
      expect(buildApiUrl("/health")).toBe(expected);
    });
  });

  describe("Headers and demo token passing", () => {
    it("attaches Content-Type and X-Demo-Token headers", async () => {
      let capturedHeaders: Headers | null = null;

      server.use(
        http.get("*/test-headers", ({ request }) => {
          capturedHeaders = request.headers;
          return HttpResponse.json({ ok: true });
        }),
      );

      await request("/test-headers");

      expect(capturedHeaders).not.null;
      expect(capturedHeaders!.get("Content-Type")).toBe("application/json");
      expect(capturedHeaders!.get("X-Demo-Token")).toBe(DEMO_TOKEN);
    });

    it("allows custom headers to be passed and merged", async () => {
      let customHeaderVal: string | null = null;

      server.use(
        http.get("*/test-custom-headers", ({ request }) => {
          customHeaderVal = request.headers.get("X-Custom-Trace");
          return HttpResponse.json({ ok: true });
        }),
      );

      await request("/test-custom-headers", {
        headers: {
          "X-Custom-Trace": "trace-12345",
        },
      });

      expect(customHeaderVal).toBe("trace-12345");
    });
  });

  describe("Status handling and error mapping", () => {
    it("throws ApiError with correct status and message on 404", async () => {
      server.use(
        http.get("*/not-found", () => {
          return new HttpResponse(null, { status: 404 });
        }),
      );

      await expect(request("/not-found")).rejects.toThrowError(ApiError);

      try {
        await request("/not-found");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(404);
        expect(apiErr.path).toBe("/not-found");
        expect(apiErr.message).toContain("failed with status 404");
      }
    });

    it("throws ApiError on 500 server error", async () => {
      server.use(
        http.post("*/server-error", () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      await expect(
        request("/server-error", { method: "POST" }),
      ).rejects.toThrowError(ApiError);
    });
  });

  describe("Timeout handling", () => {
    it("aborts when request exceeds specified timeout", async () => {
      server.use(
        http.get("*/slow-endpoint", async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ delayed: true });
        }),
      );

      // Timeout in 10ms
      await expect(request("/slow-endpoint", undefined, 10)).rejects.toThrow();
    });
  });

  describe("Typed endpoint wrappers", () => {
    it("fetchHealth returns health payload", async () => {
      const res = await fetchHealth();
      expect(res.status).toBe("ok");
      expect(res.database.available).toBe(true);
    });

    it("fetchIdentity returns identity payload", async () => {
      const res = await fetchIdentity();
      expect(res.user_id).toBe("demo-user-1");
      expect(res.is_demo_user).toBe(true);
    });

    it("fetchForecast sends default and custom params", async () => {
      const res = await fetchForecast({ horizon_days: 14, language: "en" });
      expect(res.horizon_days).toBe(14);
      expect(res.days.length).toBeGreaterThan(0);
    });

    it("fetchSavingsPlan sends goal and months", async () => {
      const res = await fetchSavingsPlan({ goal_bdt: 30000, months: 6 });
      expect(res.goal_bdt).toBe(30000);
      expect(res.months).toBe(6);
    });

    it("fetchAnomalies sends window_days and limit", async () => {
      const res = await fetchAnomalies({ window_days: 30 });
      expect(res.items.length).toBeGreaterThan(0);
    });

    it("fetchExplain sends message and language", async () => {
      const res = await fetchExplain({ message: "how to save", language: "bn" });
      expect(res.intent).toBe("savings_plan");
    });

    it("fetchCreditReadiness passes language query param", async () => {
      const res = await fetchCreditReadiness("en");
      expect(res.band).toBe("Steady");
      expect(res.not_a_decision).toBe(true);
    });

    it("fetchMetrics returns model metrics", async () => {
      const res = await fetchMetrics();
      expect(res.forecast.length).toBeGreaterThan(0);
    });

    it("fetchParseGoal returns parsed goal entity", async () => {
      const res = await fetchParseGoal("want to save 30000 in 6 months");
      expect(res.goal_bdt).toBe(30000);
      expect(res.months).toBe(6);
      expect(res.is_complete).toBe(true);
    });
  });
});
