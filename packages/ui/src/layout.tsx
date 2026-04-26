import * as React from "react";

import { cx } from "./internal";

type StackGap = "1" | "2" | "3" | "4" | "5" | "6";

export const Stack = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    gap?: StackGap;
  }
>(function Stack({ gap = "4", className, ...props }, ref) {
  return <div ref={ref} className={cx("ui-stack", `ui-stack-gap-${gap}`, className)} {...props} />;
});

export const InlineActions = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function InlineActions({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-inline-actions", className)} {...props} />;
  },
);

export const SurfaceNote = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SurfaceNote({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-surface-note", className)} {...props} />;
  },
);

export const EmptyState = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function EmptyState({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-empty-state", className)} {...props} />;
  },
);
