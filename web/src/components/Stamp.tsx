import type { ReactNode } from "react";

interface StampProps {
  children: ReactNode;
  variant?: "ink" | "muted" | "warn";
  className?: string;
}

/**
 * Section 6 / D2: Traditional Bengali Khata Ink Stamp
 * 1px rectangular border, font-mono, slight -1.5deg rotation, transparent bg.
 * Never a modern solid filled pill badge or green badge.
 */
export default function Stamp({
  children,
  variant = "muted",
  className = "",
}: StampProps) {
  const variantClass =
    variant === "ink"
      ? "stamp-ink"
      : variant === "warn"
        ? "stamp-warn"
        : "stamp-muted";

  return (
    <span className={`stamp ${variantClass} ${className}`}>
      {children}
    </span>
  );
}
