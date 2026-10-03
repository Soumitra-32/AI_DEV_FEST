import type { HTMLAttributes } from "react";
import React from "react";

interface MaterialIconProps extends HTMLAttributes<HTMLSpanElement> {
  name: string;
  size?: number;
  className?: string;
}

/**
 * Material Symbols Outlined helper component.
 * Renders icons with exact font metrics, high clarity, and zero layout shift.
 */
export default function MaterialIcon({
  name,
  size = 20,
  className = "",
  style,
  ...props
}: MaterialIconProps) {
  return (
    <span
      className={`material-symbols-outlined select-none shrink-0 ${className}`}
      style={{ fontSize: `${size}px`, lineHeight: 1, ...style }}
      aria-hidden="true"
      {...props}
    >
      {name}
    </span>
  );
}
