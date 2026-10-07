import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FeedbackWidget } from "../FeedbackWidget";
import * as api from "@/lib/api";

describe("FeedbackWidget", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders with default Bangla strings and feedback options", () => {
    render(<FeedbackWidget feature="forecast" language="bn" />);
    expect(screen.getByText("এটি কি কাজে লেগেছে?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /হ্যাঁ, কাজে লেগেছে/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /না, কাজে লাগেনি/i })).toBeInTheDocument();
    expect(screen.getByText("রেটিং দিন:")).toBeInTheDocument();
  });

  it("renders with English strings when language is 'en'", () => {
    render(<FeedbackWidget feature="savings_plan" language="en" />);
    expect(screen.getByText("Was this useful?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Yes, useful/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /No, not useful/i })).toBeInTheDocument();
    expect(screen.getByText("Rating (1–5):")).toBeInTheDocument();
  });

  it("submits thumbs up feedback and shows thank you message", async () => {
    const postFeedbackSpy = vi.spyOn(api, "postFeedback").mockResolvedValue({
      status: "recorded",
      recorded_at: "2026-10-07T12:00:00Z",
      respondent: "anon123",
      surface: "tips",
      feature: "tips",
      helpful: true,
      stored_fields: ["recorded_at", "respondent", "surface", "helpful"],
      note: "anonymised",
    });

    const user = userEvent.setup();
    render(<FeedbackWidget feature="tips" language="en" recommendationId="rec-1" />);

    const yesBtn = screen.getByRole("button", { name: /Yes, useful/i });
    await user.click(yesBtn);

    await waitFor(() => {
      expect(postFeedbackSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          feature: "tips",
          surface: "tips",
          helpful: true,
          recommendation_id: "rec-1",
        }),
      );
    });

    expect(await screen.findByText(/Thank you for your feedback!/i)).toBeInTheDocument();
  });

  it("submits 1-5 star ratings correctly", async () => {
    const postFeedbackSpy = vi.spyOn(api, "postFeedback").mockResolvedValue({
      status: "recorded",
      recorded_at: "2026-10-07T12:00:00Z",
      respondent: "anon123",
      surface: "copilot",
      feature: "copilot",
      helpful: true,
      rating: 4,
      stored_fields: ["recorded_at", "respondent", "surface", "helpful"],
      note: "anonymised",
    });

    const user = userEvent.setup();
    render(<FeedbackWidget feature="copilot" language="bn" />);

    const rate4Btn = screen.getByRole("button", { name: "Rate 4 out of 5" });
    await user.click(rate4Btn);

    await waitFor(() => {
      expect(postFeedbackSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          feature: "copilot",
          rating: 4,
          helpful: true,
        }),
      );
    });
  });

  it("shows an error note when submission fails", async () => {
    vi.spyOn(api, "postFeedback").mockRejectedValue(new Error("Network failure"));

    const user = userEvent.setup();
    render(<FeedbackWidget feature="forecast" language="en" />);

    const noBtn = screen.getByRole("button", { name: /No, not useful/i });
    await user.click(noBtn);

    expect(await screen.findByText("Failed to record")).toBeInTheDocument();
  });
});
