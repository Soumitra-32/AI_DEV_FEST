"use client";

import React, { useState } from "react";
import { postFeedback } from "@/lib/api";

interface FeedbackWidgetProps {
  feature: string;
  recommendationId?: string;
  language?: "bn" | "en";
  allowRating?: boolean;
  onSubmitted?: () => void;
}

export function FeedbackWidget({
  feature,
  recommendationId,
  language = "bn",
  allowRating = true,
  onSubmitted,
}: FeedbackWidgetProps) {
  const [submitted, setSubmitted] = useState<boolean>(false);
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [rating, setRating] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const t = {
    question: language === "bn" ? "এটি কি কাজে লেগেছে?" : "Was this useful?",
    yes: language === "bn" ? "👍 হ্যাঁ" : "👍 Yes",
    no: language === "bn" ? "👎 না" : "👎 No",
    ratingPrompt: language === "bn" ? "রেটিং দিন:" : "Rating (1–5):",
    thankYou:
      language === "bn"
        ? "মতামতের জন্য ধন্যবাদ! খতিয়ানে যুক্ত হয়েছে।"
        : "Thank you for your feedback!",
    submitting: language === "bn" ? "জমা হচ্ছে..." : "Submitting...",
  };

  const handleFeedback = async (isHelpful: boolean, selectedRating?: number) => {
    setSubmitting(true);
    setError(null);
    try {
      await postFeedback({
        feature,
        surface: feature,
        helpful: isHelpful,
        understood: true,
        acted_on: isHelpful,
        rating: selectedRating ?? rating ?? (isHelpful ? 5 : 2),
        recommendation_id: recommendationId,
      });
      setHelpful(isHelpful);
      if (selectedRating !== undefined) setRating(selectedRating);
      setSubmitted(true);
      if (onSubmitted) onSubmitted();
    } catch {
      setError(language === "bn" ? "সংরক্ষণ করা যায়নি" : "Failed to record");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="my-3 py-2 px-3 border border-[#D8CFBB] bg-[#F1F4F9] rounded-[6px] text-xs text-[#1E1B16] font-['Hind_Siliguri'] flex items-center justify-between"
      >
        <span className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-[#0054A6]" />
          {t.thankYou}
        </span>
        <span className="text-[#6A6355] text-[11px]">
          {helpful ? "👍" : "👎"} {rating ? `★ ${rating}/5` : ""}
        </span>
      </div>
    );
  }

  return (
    <div
      aria-label="Feedback"
      className="my-3 py-2.5 px-3 border border-[#D8CFBB] bg-[#FFFFFF] rounded-[6px] text-xs font-['Hind_Siliguri'] text-[#1E1B16]"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[#6A6355] font-medium">{t.question}</span>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleFeedback(true)}
            className="min-h-[36px] px-3 py-1.5 border border-[#D8CFBB] hover:border-[#0054A6] hover:bg-[#F1F4F9] rounded-[6px] font-medium text-[#1E1B16] transition-colors focus:outline-none focus:ring-1 focus:ring-[#0054A6] disabled:opacity-50"
            aria-label={language === "bn" ? "হ্যাঁ, কাজে লেগেছে" : "Yes, useful"}
          >
            {t.yes}
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleFeedback(false)}
            className="min-h-[36px] px-3 py-1.5 border border-[#D8CFBB] hover:border-[#B0431F] hover:bg-[#F1F4F9] rounded-[6px] font-medium text-[#1E1B16] transition-colors focus:outline-none focus:ring-1 focus:ring-[#B0431F] disabled:opacity-50"
            aria-label={language === "bn" ? "না, কাজে লাগেনি" : "No, not useful"}
          >
            {t.no}
          </button>
        </div>
      </div>

      {allowRating && (
        <div className="mt-2.5 pt-2 border-t border-[#D8CFBB] flex items-center justify-between text-[11px] text-[#6A6355]">
          <span>{t.ratingPrompt}</span>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                disabled={submitting}
                onClick={() => handleFeedback(star >= 3, star)}
                className={`w-7 h-7 flex items-center justify-center rounded-[4px] border border-[#D8CFBB] font-mono text-[11px] transition-colors ${
                  rating === star
                    ? "bg-[#0054A6] text-white border-[#0054A6]"
                    : "hover:bg-[#F1F4F9] hover:border-[#0054A6] text-[#1E1B16]"
                }`}
                aria-label={`Rate ${star} out of 5`}
              >
                {star}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <p className="mt-1 text-[#B0431F] text-[11px]">{error}</p>}
    </div>
  );
}
