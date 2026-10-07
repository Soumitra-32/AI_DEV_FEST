"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useLanguage } from "@/components/LangToggle";
import { fetchSavingsPlan } from "@/lib/api";
import type { SavingsPlanResponse } from "@/lib/api";

const DEFAULT_GOAL = 30000;
const DEFAULT_MONTHS = 6;

export interface SavingsPlanFormProps {
  initialGoal?: string | number;
  initialMonths?: string | number;
  onSubmit?: (payload: { goal_bdt: number; months: number }) => void | Promise<void>;
  onSuccess?: (plan: SavingsPlanResponse) => void;
  onError?: (error: string) => void;
  busy?: boolean;
  error?: string | null;
}

export default function SavingsPlanForm({
  initialGoal,
  initialMonths,
  onSubmit,
  onSuccess,
  onError,
  busy: controlledBusy,
  error: controlledError,
}: SavingsPlanFormProps) {
  const { tr } = useLanguage();

  const [goal, setGoal] = useState<string>(() =>
    initialGoal !== undefined ? String(initialGoal) : String(DEFAULT_GOAL),
  );
  const [months, setMonths] = useState<string>(() =>
    initialMonths !== undefined ? String(initialMonths) : String(DEFAULT_MONTHS),
  );
  const [internalBusy, setInternalBusy] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (initialGoal !== undefined) {
      setGoal(String(initialGoal));
    }
  }, [initialGoal]);

  useEffect(() => {
    if (initialMonths !== undefined) {
      setMonths(String(initialMonths));
    }
  }, [initialMonths]);

  const isBusy = controlledBusy ?? internalBusy;
  const displayError = controlledError ?? validationError;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    const goalBdt = Number(goal);
    const monthsCount = Number(months);

    // Validate numeric values and edge cases
    if (
      goal.trim() === "" ||
      !Number.isFinite(goalBdt) ||
      goalBdt <= 0 ||
      isNaN(goalBdt)
    ) {
      const err = tr("error.title");
      setValidationError(err);
      onError?.(err);
      return;
    }

    if (
      months.trim() === "" ||
      !Number.isFinite(monthsCount) ||
      monthsCount < 1 ||
      isNaN(monthsCount)
    ) {
      const err = tr("error.title");
      setValidationError(err);
      onError?.(err);
      return;
    }

    const payload = {
      goal_bdt: goalBdt,
      months: Math.round(monthsCount),
    };

    if (onSubmit) {
      try {
        await onSubmit(payload);
      } catch (err) {
        const message = err instanceof Error ? err.message : tr("error.title");
        setValidationError(message);
        onError?.(message);
      }
      return;
    }

    // Default self-contained flow using fetchSavingsPlan
    setInternalBusy(true);
    try {
      const res = await fetchSavingsPlan(payload);
      setInternalBusy(false);
      onSuccess?.(res);
    } catch {
      setInternalBusy(false);
      const err = tr("error.title");
      setValidationError(err);
      onError?.(err);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="savings-plan-form"
      className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label htmlFor="goal-input" className="text-xs font-mono uppercase text-ink-muted block">
            {tr("plan.goal")}
          </label>
          <input
            id="goal-input"
            type="number"
            min={500}
            step={500}
            value={goal}
            disabled={isBusy}
            onChange={(e) => setGoal(e.target.value)}
            className="w-full h-14 bg-[#F1F4F9] border border-[#D8CFBB] px-4 font-serif-bn text-xl font-bold text-[#1E1B16] rounded-[6px] focus:outline-none focus:border-[#0054A6] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="months-input" className="text-xs font-mono uppercase text-[#6A6355] block">
            {tr("plan.months")}
          </label>
          <input
            id="months-input"
            type="number"
            min={1}
            max={36}
            value={months}
            disabled={isBusy}
            onChange={(e) => setMonths(e.target.value)}
            className="w-full h-14 bg-[#F1F4F9] border border-[#D8CFBB] px-4 font-mono text-lg text-[#1E1B16] rounded-[6px] focus:outline-none focus:border-[#0054A6] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isBusy}
        className="w-full min-h-[48px] h-14 bg-[#0054A6] hover:bg-[#003E7E] text-white text-[17px] font-medium rounded-[6px] transition-colors cursor-pointer border-0 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {isBusy ? tr("plan.calculating") : tr("plan.submit")}
      </button>

      {displayError && (
        <div
          role="alert"
          className="bg-surface/50 border-l-2 border-brickRed border-t border-b border-r border-rule p-4 text-brickRed text-sm font-mono"
        >
          {displayError}
        </div>
      )}
    </form>
  );
}
