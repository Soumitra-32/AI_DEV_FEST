import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import LangToggle, { LanguageProvider, useLanguage } from "@/components/LangToggle";
import { formatBDT, formatDigits } from "@/lib/i18n";

function SampleConsumer() {
  const { lang, tr } = useLanguage();
  return (
    <div>
      <span data-testid="app-title">{tr("appName")}</span>
      <span data-testid="plan-title">{tr("plan.title")}</span>
      <span data-testid="formatted-money">{formatBDT(12500, lang)}</span>
      <span data-testid="digits">{formatDigits("123", lang)}</span>
    </div>
  );
}

describe("LangToggle & LanguageProvider", () => {
  it("defaults to Bangla ('bn') and renders Bengali copy and numerals", () => {
    render(
      <LanguageProvider>
        <LangToggle />
        <SampleConsumer />
      </LanguageProvider>,
    );

    expect(screen.getByTestId("app-title")).toHaveTextContent("সঞ্চয় Copilot");
    expect(screen.getByTestId("plan-title")).toHaveTextContent("আপনার সঞ্চয় পরিকল্পনা");
    expect(screen.getByTestId("formatted-money")).toHaveTextContent("৳১২,৫০০");
    expect(screen.getByTestId("digits")).toHaveTextContent("১২৩");
  });

  it("switches to English when clicking EN, updates document and persists to localStorage", async () => {
    const user = userEvent.setup();

    render(
      <LanguageProvider>
        <LangToggle />
        <SampleConsumer />
      </LanguageProvider>,
    );

    const enButton = screen.getByRole("button", { name: "EN" });
    await user.click(enButton);

    expect(screen.getByTestId("app-title")).toHaveTextContent("Shonchoy Copilot");
    expect(screen.getByTestId("plan-title")).toHaveTextContent("Your Savings Plan");
    expect(screen.getByTestId("formatted-money")).toHaveTextContent("৳12,500");
    expect(screen.getByTestId("digits")).toHaveTextContent("123");
    expect(localStorage.getItem("shonchoy_lang")).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });

  it("switches back to Bangla when clicking বাংলা", async () => {
    const user = userEvent.setup();

    render(
      <LanguageProvider>
        <LangToggle />
        <SampleConsumer />
      </LanguageProvider>,
    );

    // Switch to EN first
    await user.click(screen.getByRole("button", { name: "EN" }));
    expect(localStorage.getItem("shonchoy_lang")).toBe("en");

    // Switch back to BN
    await user.click(screen.getByRole("button", { name: "বাংলা" }));
    expect(screen.getByTestId("app-title")).toHaveTextContent("সঞ্চয় Copilot");
    expect(localStorage.getItem("shonchoy_lang")).toBe("bn");
    expect(document.documentElement.lang).toBe("bn");
  });

  it("restores language selection from localStorage on mount", () => {
    localStorage.setItem("shonchoy_lang", "en");

    render(
      <LanguageProvider>
        <LangToggle />
        <SampleConsumer />
      </LanguageProvider>,
    );

    expect(screen.getByTestId("app-title")).toHaveTextContent("Shonchoy Copilot");
    expect(document.documentElement.lang).toBe("en");
  });
});
