import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import SavingsPlanForm from "@/components/SavingsPlanForm";
import { LanguageProvider } from "@/components/LangToggle";
import { server } from "@/test/msw/server";
import { mockSavingsPlanResponse } from "@/test/msw/handlers";

describe("SavingsPlanForm", () => {
  it("renders with default initial values", () => {
    render(
      <LanguageProvider>
        <SavingsPlanForm />
      </LanguageProvider>,
    );

    const goalInput = screen.getByLabelText(/লক্ষ্যের পরিমাণ|Goal/i) as HTMLInputElement;
    const monthsInput = screen.getByLabelText(/সময়সীমা|Months/i) as HTMLInputElement;

    expect(goalInput.value).toBe("30000");
    expect(monthsInput.value).toBe("6");
  });

  it("calls onSubmit callback with parsed numbers on valid submission", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal={25000}
          initialMonths={5}
          onSubmit={handleSubmit}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledWith({
      goal_bdt: 25000,
      months: 5,
    });
  });

  it("validates empty goal and shows error without submitting", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    const handleError = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal=""
          initialMonths={6}
          onSubmit={handleSubmit}
          onError={handleError}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(handleError).toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("validates zero or negative goal input edge cases", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal="0"
          initialMonths={6}
          onSubmit={handleSubmit}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("validates months less than 1 edge case", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal={50000}
          initialMonths="0"
          onSubmit={handleSubmit}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("disables inputs and button when busy is true", () => {
    render(
      <LanguageProvider>
        <SavingsPlanForm busy={true} />
      </LanguageProvider>,
    );

    const goalInput = screen.getByLabelText(/লক্ষ্যের পরিমাণ|Goal/i);
    const monthsInput = screen.getByLabelText(/সময়সীমা|Months/i);
    const submitBtn = screen.getByRole("button");

    expect(goalInput).toBeDisabled();
    expect(monthsInput).toBeDisabled();
    expect(submitBtn).toBeDisabled();
    expect(submitBtn).toHaveTextContent(/হিসাব করা হচ্ছে|Calculating/);
  });

  it("self-contained flow: calls MSW /savings-plan and triggers onSuccess", async () => {
    const user = userEvent.setup();
    const handleSuccess = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal={30000}
          initialMonths={6}
          onSuccess={handleSuccess}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(handleSuccess).toHaveBeenCalledWith(
        expect.objectContaining({
          feasible: mockSavingsPlanResponse.feasible,
          goal_bdt: mockSavingsPlanResponse.goal_bdt,
        }),
      );
    });
  });

  it("self-contained flow: handles API failure and triggers onError", async () => {
    server.use(
      http.post("*/savings-plan", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const user = userEvent.setup();
    const handleError = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal={30000}
          initialMonths={6}
          onError={handleError}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(handleError).toHaveBeenCalled();
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("handles decimal months by rounding", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(
      <LanguageProvider>
        <SavingsPlanForm
          initialGoal={15000}
          initialMonths="5.8"
          onSubmit={handleSubmit}
        />
      </LanguageProvider>,
    );

    const submitBtn = screen.getByRole("button", { name: /পরিকল্পনা হিসাব করুন|Calculate Plan/i });
    await user.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledWith({
      goal_bdt: 15000,
      months: 6,
    });
  });
});
