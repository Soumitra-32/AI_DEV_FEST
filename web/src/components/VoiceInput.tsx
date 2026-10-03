"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff } from "lucide-react";
import { useLanguage } from "@/components/LangToggle";

interface VoiceInputProps {
  onResult?: (text: string) => void;
  onSubmitText?: (text: string) => void;
  initialValue?: string;
  placeholder?: string;
}

export default function VoiceInput({
  onResult,
  onSubmitText,
  initialValue = "",
  placeholder,
}: VoiceInputProps) {
  const { lang, tr } = useLanguage();
  const [text, setText] = useState(initialValue);
  const [listening, setListening] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // Live words while speaking (cleared on final result).
  const [interim, setInterim] = useState("");
  // Final voice transcript waiting for the user's confirmation. Nothing
  // routes anywhere until they press ✓ — a mistranscription can no longer
  // silently become a wrong plan.
  const [pendingVoice, setPendingVoice] = useState<string | null>(null);
  // The live instance must survive re-renders: without this ref there is no
  // handle to stop it, so the "stop" button can never actually stop the mic.
  const recognitionRef = useRef<any>(null);

  // Never leave the mic open when the component unmounts.
  useEffect(() => {
    return () => {
      try {
        recognitionRef.current?.abort();
      } catch {
        /* already stopped */
      }
      recognitionRef.current = null;
    };
  }, []);

  const toggleListening = useCallback(() => {
    setErrorMsg(null);
    setInterim("");
    // Tapping mic with a pending transcript means "retry": discard and listen fresh.
    setPendingVoice(null);
    // Second click while live: stop the REAL instance (onend flips the UI).
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        setListening(false);
      }
      return;
    }
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: any }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setErrorMsg(tr("voice.unsupported"));
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = lang === "bn" ? "bn-BD" : "en-US";
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 3;

      recognition.onstart = () => setListening(true);
      recognition.onend = () => {
        setListening(false);
        setInterim("");
        recognitionRef.current = null;
      };
      recognition.onerror = (event: any) => {
        setListening(false);
        setInterim("");
        recognitionRef.current = null;
        // Tell the truth about WHAT failed: every error used to show
        // "unsupported", which sent users to change browsers for what was
        // actually a blocked mic or lost network.
        const code = event?.error as string | undefined;
        if (code === "not-allowed" || code === "service-not-allowed") {
          setErrorMsg(tr("voice.denied"));
        } else if (code === "audio-capture") {
          setErrorMsg(tr("voice.nomic"));
        } else if (code === "network") {
          setErrorMsg(tr("voice.offline"));
        } else if (code === "no-speech") {
          setErrorMsg(tr("voice.nospeech"));
        } else {
          setErrorMsg(tr("voice.unsupported"));
        }
      };

      recognition.onresult = (event: any) => {
        let interimText = "";
        let finalText = "";
        const results = event.results ?? [];
        for (let i = event.resultIndex ?? 0; i < results.length; i++) {
          const result = results[i];
          if (result.isFinal) {
            // Best non-empty alternative; top choice is often whitespace
            // when accented speech confuses the model.
            for (let a = 0; a < result.length; a++) {
              const candidate = result[a]?.transcript ?? "";
              if (candidate.trim()) {
                finalText = candidate;
                break;
              }
            }
          } else {
            interimText += result[0]?.transcript ?? "";
          }
        }
        if (interimText) {
          setInterim(interimText);
        }
        if (finalText.trim()) {
          const heard = finalText.trim();
          setText(heard);
          setInterim("");
          setPendingVoice(heard);
          onResult?.(heard);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setListening(false);
      recognitionRef.current = null;
      setErrorMsg(tr("voice.unsupported"));
    }
  }, [lang, onResult, onSubmitText, tr]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      setPendingVoice(null);
      onSubmitText?.(text.trim());
    }
  };

  const handleConfirmVoice = () => {
    if (pendingVoice) {
      setPendingVoice(null);
      onSubmitText?.(pendingVoice);
    }
  };

  const handleRetryVoice = () => {
    setPendingVoice(null);
    setInterim("");
    toggleListening();
  };

  return (
    <div className="space-y-2">
      <form onSubmit={handleSubmit} className="space-y-1.5 max-w-2xl">
        <label htmlFor="voice-search-input" className="text-xs font-mono uppercase text-ink-muted block">
          {tr("voice.label")}
        </label>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              id="voice-search-input"
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={placeholder ?? tr("voice.placeholder")}
              className="w-full h-12 bg-surface border border-rule px-4 text-sm font-hind text-ink placeholder-ink-muted/70 focus:outline-none focus:border-ink transition-colors rounded-none"
            />
          </div>
          {/* Flat Mic Button - No gradient, no shadow */}
          <button
            type="button"
            onClick={toggleListening}
            title={listening ? tr("voice.listening") : tr("voice.speak")}
            aria-label={listening ? tr("voice.listening") : tr("voice.speak")}
            className={`h-12 w-12 bg-surface border flex items-center justify-center shrink-0 transition-colors rounded-none ${
              listening
                ? "border-brickRed text-brickRed"
                : "border-rule text-ink hover:border-ink"
            }`}
          >
            {listening ? (
              <MicOff className="w-5 h-5 stroke-[1.5] animate-pulse" />
            ) : (
              <Mic className="w-5 h-5 stroke-[1.5]" />
            )}
          </button>
        </div>
      </form>

      {listening && (
        <div className="text-xs font-mono text-brickRed flex items-center gap-1.5">
          <span className="w-2 h-2 bg-brickRed rounded-full animate-ping" />
          <span>{tr("voice.listening")} ({lang === "bn" ? "বাংলা" : "English"})</span>
        </div>
      )}

      {listening && interim && (
        <p className="text-sm font-hind text-ink-muted mt-1">{interim}…</p>
      )}

      {pendingVoice && !listening && (
        <div className="bg-surface border border-rule p-3 mt-1 space-y-2 max-w-2xl rounded-none">
          <p className="text-sm font-hind text-ink">
            {tr("voice.heard")} <strong>“{pendingVoice}”</strong>
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleConfirmVoice}
              className="h-10 px-4 bg-primaryGreen text-white text-sm font-medium hover:opacity-95 transition rounded-none"
            >
              ✓ {tr("voice.confirm")}
            </button>
            <button
              type="button"
              onClick={handleRetryVoice}
              className="h-10 px-4 bg-surface border border-rule text-sm font-medium text-ink hover:border-ink transition rounded-none"
            >
              {tr("voice.retry")}
            </button>
          </div>
        </div>
      )}

      {errorMsg && (
        <p className="text-xs font-mono text-brickRed mt-1">{errorMsg}</p>
      )}
    </div>
  );
}
