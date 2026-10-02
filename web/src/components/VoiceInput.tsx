"use client";

import { useCallback, useState } from "react";
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

  const toggleListening = useCallback(() => {
    setErrorMsg(null);
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: any }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setErrorMsg(tr("voice.unsupported"));
      return;
    }

    if (listening) {
      setListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = lang === "bn" ? "bn-BD" : "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setListening(true);
      recognition.onend = () => setListening(false);
      recognition.onerror = () => {
        setListening(false);
        setErrorMsg(tr("voice.unsupported"));
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results?.[0]?.[0]?.transcript ?? "";
        if (transcript) {
          setText(transcript);
          onResult?.(transcript);
          onSubmitText?.(transcript);
        }
      };

      recognition.start();
    } catch {
      setListening(false);
      setErrorMsg(tr("voice.unsupported"));
    }
  }, [lang, listening, onResult, onSubmitText, tr]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      onSubmitText?.(text.trim());
    }
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
              className="w-full h-12 bg-surface border border-rule rounded-ledger px-4 text-sm font-hind text-ink placeholder-ink-muted/70 focus:outline-none focus:border-ink transition-colors"
            />
          </div>
          {/* Flat Mic Button - No gradient, no shadow */}
          <button
            type="button"
            onClick={toggleListening}
            title={listening ? tr("voice.listening") : tr("voice.speak")}
            aria-label={listening ? tr("voice.listening") : tr("voice.speak")}
            className={`h-12 w-12 bg-surface border rounded-ledger flex items-center justify-center shrink-0 transition-colors ${
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

      {errorMsg && (
        <p className="text-xs font-mono text-brickRed mt-1">{errorMsg}</p>
      )}
    </div>
  );
}
