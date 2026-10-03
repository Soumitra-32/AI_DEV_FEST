import type { ReactNode } from "react";

interface StampProps {
  children: ReactNode;
  variant?: "ink" | "muted" | "warn" | "blue";
  className?: string;
}

/**
 * Institutional Khata Ink Stamp
 * 1px rectangular border, font-mono, 4px radius, transparent bg.
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
        : variant === "blue"
          ? "stamp-blue"
          : "stamp-muted";

  return (
    <span className={`stamp ${variantClass} ${className}`}>
      {children}
    </span>
  );
}
