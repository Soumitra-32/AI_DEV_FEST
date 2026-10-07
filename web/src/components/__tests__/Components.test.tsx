import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { usePathname } from "next/navigation";
import { describe, expect, it, vi } from "vitest";
import Stamp from "@/components/Stamp";
import SpendingSummary from "@/components/SpendingSummary";
import FeeSavingCard from "@/components/FeeSavingCard";
import SuggestionChips from "@/components/SuggestionChips";
import DoNothingToggle from "@/components/DoNothingToggle";
import InsightCard from "@/components/InsightCard";
import AnomalyCard from "@/components/AnomalyCard";
import BottomNav from "@/components/BottomNav";
import VoiceInput from "@/components/VoiceInput";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import LangToggle, { LanguageProvider } from "@/components/LangToggle";
import type { AnomalyItem, FeeSwitchSuggestion, Provenance } from "@/lib/api";

const mockFeeSwitch: FeeSwitchSuggestion = {
  cash_out_count: 4,
  cash_out_volume_bdt: 10000,
  fee_paid_bdt: 185,
  alternative_channel: "bangla_qr",
  alternative_fee_bdt: 0,
  potential_saving_bdt: 185,
  adoption_range: "30%–70%",
  bangla_qr_eligible_count: 4,
  bangla_qr_eligible_volume_bdt: 10000,
};

const mockProvenance: Provenance = {
  prediction: "14-day cash forecast",
  assumption: "Recent spending patterns continue",
  explanation: "Calculated using Gradient Boosting on transactional history",
  source: "model",
};

describe("Additional Frontend Components", () => {
  describe("Stamp", () => {
    it("renders all stamp variants", () => {
      const { rerender } = render(<Stamp variant="ink">Computed</Stamp>);
      expect(screen.getByText("Computed")).toHaveClass("stamp-ink");

      rerender(<Stamp variant="warn">Warning</Stamp>);
      expect(screen.getByText("Warning")).toHaveClass("stamp-warn");

      rerender(<Stamp variant="blue">Blue Badge</Stamp>);
      expect(screen.getByText("Blue Badge")).toHaveClass("stamp-blue");

      rerender(<Stamp variant="muted">Muted</Stamp>);
      expect(screen.getByText("Muted")).toHaveClass("stamp-muted");
    });
  });

  describe("SpendingSummary", () => {
    it("renders spending summary rows with fee data", () => {
      render(
        <LanguageProvider>
          <SpendingSummary feeSwitch={mockFeeSwitch} windowDays={30} />
        </LanguageProvider>,
      );

      expect(screen.getByText(/ক্যাশ-আউট সংখ্যা|Cash withdrawals/)).toBeInTheDocument();
      expect(screen.getByText(/পরিশোধিত ফি|Fees paid/)).toBeInTheDocument();
    });

    it("renders null when feeSwitch is not provided", () => {
      const { container } = render(
        <LanguageProvider>
          <SpendingSummary feeSwitch={null} />
        </LanguageProvider>,
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe("FeeSavingCard", () => {
    it("renders fee saving details and Bangla QR policy info in both languages", async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <LanguageProvider>
          <FeeSavingCard feeSwitch={mockFeeSwitch} />
          <LangToggle />
        </LanguageProvider>,
      );

      expect(
        screen.getByText(/দোকানে QR পেমেন্ট: কোনো চার্জ নেই|Pay Merchants by QR: Zero Fee/),
      ).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "EN" }));
      expect(screen.getByText("Pay Merchants by QR: Zero Fee")).toBeInTheDocument();

      // Test without eligible count
      rerender(
        <LanguageProvider>
          <FeeSavingCard feeSwitch={{ ...mockFeeSwitch, bangla_qr_eligible_count: undefined }} />
        </LanguageProvider>,
      );
    });
  });

  describe("SuggestionChips", () => {
    it("renders chips and triggers onSelectQuery callback on click", async () => {
      const user = userEvent.setup();
      const handleSelect = vi.fn();

      render(
        <LanguageProvider>
          <SuggestionChips onSelectQuery={handleSelect} />
        </LanguageProvider>,
      );

      const links = screen.getAllByRole("link");
      expect(links.length).toBe(3);

      await user.click(links[0]);
      expect(handleSelect).toHaveBeenCalled();
    });
  });

  describe("DoNothingToggle", () => {
    it("toggles open and records decision", async () => {
      const user = userEvent.setup();

      render(
        <LanguageProvider>
          <DoNothingToggle costBdt={1200} months={6} />
        </LanguageProvider>,
      );

      const toggleHeader = screen.getByText(/কিছু না করলে কী হবে\?|What if I do nothing\?/);
      await user.click(toggleHeader);

      expect(
        screen.getByText(/সম্পূর্ণ নিরপেক্ষ এবং স্বাভাবিক একটি পথ|A completely neutral and natural path/),
      ).toBeInTheDocument();

      const confirmBtn = screen.getByRole("button", { name: /ঠিক আছে|Okay/ });
      await user.click(confirmBtn);

      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("handles dismiss click to close the drawer, and handles months != 6", async () => {
      const user = userEvent.setup();

      const { rerender } = render(
        <LanguageProvider>
          <DoNothingToggle costBdt={1200} months={12} />
        </LanguageProvider>,
      );

      const toggleHeader = screen.getByText(/কিছু না করলে কী হবে\?|What if I do nothing\?/);
      await user.click(toggleHeader);

      const dismissBtn = screen.getByRole("button", { name: /পরে দেখব|Later/ });
      await user.click(dismissBtn);

      expect(screen.queryByRole("status")).not.toBeInTheDocument();

      // In English mode with no cost
      rerender(
        <LanguageProvider>
          <LangToggle />
          <DoNothingToggle months={12} costBdt={0} />
        </LanguageProvider>,
      );
      await user.click(screen.getByRole("button", { name: "EN" }));
      await user.click(screen.getByText("What if I do nothing?"));
      expect(screen.getByText(/After 12 months, savings will be ৳0/)).toBeInTheDocument();
    });
  });

  describe("NotADecisionBanner", () => {
    it("renders for every route variant and with custom contextNote", () => {
      const routes = ["home", "forecast", "plan", "spending", "tips", "signal", "metrics"] as const;

      for (const route of routes) {
        const { unmount } = render(
          <LanguageProvider>
            <NotADecisionBanner route={route} />
          </LanguageProvider>,
        );
        unmount();
      }

      render(
        <LanguageProvider>
          <NotADecisionBanner contextNote="Special Custom Legal Note" />
        </LanguageProvider>,
      );
      expect(screen.getByText("Special Custom Legal Note")).toBeInTheDocument();
    });
  });

  describe("InsightCard", () => {
    it("renders three-layer provenance with rule, model, template sources", () => {
      const { rerender } = render(
        <LanguageProvider>
          <InsightCard provenance={mockProvenance} />
        </LanguageProvider>,
      );

      expect(screen.getByText(/পূর্বাভাস|Prediction/)).toBeInTheDocument();
      expect(screen.getByText(/যা ধরে নিচ্ছি|Assumption/)).toBeInTheDocument();
      expect(screen.getByText(/কারণ|Reason/)).toBeInTheDocument();

      rerender(
        <LanguageProvider>
          <InsightCard
            provenance={{
              prediction: "fixed template answered query",
              assumption: "template path runs on rule defaults",
              explanation: "Intent: forecast failed a check",
              source: "template",
            }}
          />
        </LanguageProvider>,
      );

      expect(screen.getByText(/নির্ভরযোগ্য খতিয়ান/)).toBeInTheDocument();
    });

    it("handles all known backend template strings in Bangla and English", async () => {
      const testCases = [
        "Next 14 days from June net about 5,000 taka",
        "14-day mean flow from the trained model",
        "Level from your own trailing-28-day average",
        "Baseline outlook for Trailing 7-day average",
        "Tightest day is day 28",
        "No pressure day in this window",
        "30,000 in 6 months needs 5,000/month; you can keep about 7,000/month after the buffer",
        "Plan feasible with surplus",
        "Plan not feasible with surplus",
        "Monthly surplus is the 14-day forecast scaled",
        "The forecast covers the goal with the safety buffer kept",
        "Pick a trade-off below or free up monthly cash",
        "A goal amount and a horizon are required",
        "The solver never runs on a guessed number",
        "least typical payments ranked against your own history",
        "No payment of your last 30 days stands out against your own history",
        "Unusual means far from your own recent pattern",
        "cash-out(s) cost fee, switching to qr saves money",
        "No cash-out fee stands out",
        "Your recent behaviour sits in the steady band",
        "Based only on the transactions you can see in the khata",
      ];

      for (const text of testCases) {
        const { unmount } = render(
          <LanguageProvider>
            <InsightCard
              provenance={{
                prediction: text,
                assumption: text,
                explanation: text,
                source: "model",
              }}
            />
          </LanguageProvider>,
        );
        unmount();
      }
    });

    it("renders custom title and children in English mode", async () => {
      const user = userEvent.setup();

      render(
        <LanguageProvider>
          <LangToggle />
          <InsightCard title="Custom Title" provenance={{ ...mockProvenance, source: "llm" }}>
            <div data-testid="child-block">Custom Child Content</div>
          </InsightCard>
        </LanguageProvider>,
      );

      await user.click(screen.getByRole("button", { name: "EN" }));
      expect(screen.getByText("Custom Title")).toBeInTheDocument();
      expect(screen.getByTestId("child-block")).toBeInTheDocument();
    });
  });

  describe("AnomalyCard", () => {
    it("renders all anomaly patterns and channels", () => {
      const reasons: AnomalyItem[] = [
        {
          transaction_id: "tx-1",
          timestamp: "2026-10-05T14:30:00Z",
          amount_bdt: 2000,
          channel: "cash_out",
          category: "personal",
          anomaly_type: "amount_anomaly",
          score: 0.9,
          reason:
            "Rapid repeat near ৳2,000 (2,000 BDT) — potential transaction splitting under Payment & Settlement Systems Act, 2024 monitoring",
          suggested_action: "bangla_qr" as any,
          suggested_channel: "bangla_qr",
        },
        {
          transaction_id: "tx-2",
          timestamp: "2026-10-05T14:30:00Z",
          amount_bdt: 5000,
          channel: "merchant",
          category: "shop",
          anomaly_type: "time_anomaly",
          score: 0.8,
          reason: "Happened at 02:30, outside your usual hours",
          suggested_action: "review" as any,
          suggested_channel: "p2p",
        },
        {
          transaction_id: "tx-3",
          timestamp: "2026-10-05T14:30:00Z",
          amount_bdt: 1000,
          channel: "p2p",
          category: "transfer",
          anomaly_type: "frequency_anomaly",
          score: 0.7,
          reason: "Another very similar payment within 5 minutes",
          suggested_action: "app transfer" as any,
          suggested_channel: "cash_out",
        },
        {
          transaction_id: "tx-4",
          timestamp: "2026-10-05T14:30:00Z",
          amount_bdt: 500,
          channel: "bill_pay",
          category: "utility",
          anomaly_type: "channel_anomaly",
          score: 0.6,
          reason: "About 3.5x your own average payment",
          suggested_action: "none" as any,
          suggested_channel: null,
        },
        {
          transaction_id: "tx-5",
          timestamp: "2026-10-05T14:30:00Z",
          amount_bdt: 1200,
          channel: "cash_out",
          category: "personal",
          anomaly_type: null,
          score: null,
          reason: "Timing is unusual for you (03:00 is not one of your usual hours)",
          suggested_action: "unknown" as any,
          suggested_channel: null,
        },
      ];

      for (const item of reasons) {
        const { unmount } = render(
          <LanguageProvider>
            <AnomalyCard item={item} />
          </LanguageProvider>,
        );
        unmount();
      }
    });
  });

  describe("BottomNav", () => {
    it("renders primary tabs and handles active routes", async () => {
      const user = userEvent.setup();

      // Test route indices
      for (const path of ["/", "/forecast", "/plan", "/spending", "/tips", "/signal", "/metrics"]) {
        vi.mocked(usePathname).mockReturnValue(path);
        const { unmount } = render(
          <LanguageProvider>
            <BottomNav />
          </LanguageProvider>,
        );
        unmount();
      }

      vi.mocked(usePathname).mockReturnValue("/");
      render(
        <LanguageProvider>
          <BottomNav />
        </LanguageProvider>,
      );

      expect(screen.getByText(/হোম|Home/)).toBeInTheDocument();

      // Open drawer
      const moreBtn = screen.getByRole("button", { name: /আরও|More/ });
      await user.click(moreBtn);

      expect(screen.getByText(/খরচ|Expenditure/)).toBeInTheDocument();

      // Close drawer via Escape key
      await user.keyboard("{Escape}");
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  describe("VoiceInput", () => {
    it("renders input field and handles typing and submit", async () => {
      const user = userEvent.setup();
      const handleSubmit = vi.fn();

      render(
        <LanguageProvider>
          <VoiceInput onSubmitText={handleSubmit} />
        </LanguageProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "Want to save 30000 in 6 months{Enter}");

      expect(handleSubmit).toHaveBeenCalledWith("Want to save 30000 in 6 months");
    });

    it("handles speech recognition error callbacks for all error codes", async () => {
      let instance: any = null;
      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = "";
        onstart: (() => void) | null = null;
        onerror: ((event: any) => void) | null = null;
        onend: (() => void) | null = null;

        constructor() {
          instance = this;
        }

        start() {
          this.onstart?.();
        }
        stop() {
          this.onend?.();
        }
        abort() {
          this.onend?.();
        }
      }

      (window as any).webkitSpeechRecognition = MockSpeechRecognition;

      const user = userEvent.setup();
      render(
        <LanguageProvider>
          <VoiceInput />
        </LanguageProvider>,
      );

      const micBtn = screen.getByRole("button", { name: /মুখে বলুন|বলুন|Speak/i });

      // not-allowed
      await user.click(micBtn);
      act(() => {
        instance?.onerror?.({ error: "not-allowed" });
      });
      expect(await screen.findByText(/মাইকে অনুমতি দিন|Please allow the mic/i)).toBeInTheDocument();

      // audio-capture
      await user.click(micBtn);
      act(() => {
        instance?.onerror?.({ error: "audio-capture" });
      });
      expect(await screen.findByText(/কোনো মাইক পাওয়া যায়নি|No microphone detected/i)).toBeInTheDocument();

      // network
      await user.click(micBtn);
      act(() => {
        instance?.onerror?.({ error: "network" });
      });
      expect(await screen.findByText(/ইন্টারনেট সংযোগ প্রয়োজন|Voice input requires internet/i)).toBeInTheDocument();

      // no-speech
      await user.click(micBtn);
      act(() => {
        instance?.onerror?.({ error: "no-speech" });
      });
      expect(await screen.findByText(/কোনো কথা শোনা যায়নি|No speech detected/i)).toBeInTheDocument();

      // other error
      await user.click(micBtn);
      act(() => {
        instance?.onerror?.({ error: "other" });
      });
      expect(await screen.findByText(/এই ফোনে ভয়েস কাজ করে না|Voice does not work/i)).toBeInTheDocument();
    });

    it("handles speech recognition result, confirm, and retry actions", async () => {
      let instance: any = null;
      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = "";
        onstart: (() => void) | null = null;
        onresult: ((event: any) => void) | null = null;
        onerror: ((event: any) => void) | null = null;
        onend: (() => void) | null = null;

        constructor() {
          instance = this;
        }

        start() {
          this.onstart?.();
        }
        stop() {
          this.onend?.();
        }
        abort() {
          this.onend?.();
        }
      }

      (window as any).webkitSpeechRecognition = MockSpeechRecognition;

      const user = userEvent.setup();
      const handleSubmit = vi.fn();
      const handleResult = vi.fn();

      render(
        <LanguageProvider>
          <VoiceInput onResult={handleResult} onSubmitText={handleSubmit} />
        </LanguageProvider>,
      );

      const micBtn = screen.getByRole("button", { name: /মুখে বলুন|বলুন|Speak/i });
      await user.click(micBtn);

      // Simulate interim followed by final result
      act(() => {
        instance?.onresult?.({
          resultIndex: 0,
          results: [
            Object.assign([{ transcript: "Save 50000" }], { isFinal: false }),
          ],
        });
      });

      act(() => {
        instance?.onresult?.({
          resultIndex: 0,
          results: [
            Object.assign([{ transcript: "Save 50000" }], { isFinal: true }),
          ],
        });
        instance?.onend?.();
      });

      expect(handleResult).toHaveBeenCalledWith("Save 50000");

      // Test Retry button
      const retryBtn = await screen.findByRole("button", { name: /আবার বলুন|Speak again/i });
      await user.click(retryBtn);

      // Listen again and confirm
      await user.click(micBtn);
      act(() => {
        instance?.onresult?.({
          resultIndex: 0,
          results: [
            Object.assign([{ transcript: "Save 30000 in 6 months" }], { isFinal: true }),
          ],
        });
        instance?.onend?.();
      });

      const confirmBtn = await screen.findByRole("button", { name: /হিসাব করুন|Calculate/i });
      await user.click(confirmBtn);

      expect(handleSubmit).toHaveBeenCalledWith("Save 30000 in 6 months");
    });

    it("displays error when SpeechRecognition is unsupported in window", async () => {
      const originalWebkit = (window as any).webkitSpeechRecognition;
      const originalStandard = (window as any).SpeechRecognition;
      delete (window as any).webkitSpeechRecognition;
      delete (window as any).SpeechRecognition;

      const user = userEvent.setup();
      render(
        <LanguageProvider>
          <VoiceInput />
        </LanguageProvider>,
      );

      const micBtn = screen.getByRole("button", { name: /মুখে বলুন|বলুন|Speak/i });
      await user.click(micBtn);

      expect(await screen.findByText(/এই ফোনে ভয়েস কাজ করে না|Voice does not work/i)).toBeInTheDocument();

      (window as any).webkitSpeechRecognition = originalWebkit;
      (window as any).SpeechRecognition = originalStandard;
    });
  });
});
