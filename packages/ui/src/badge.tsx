import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cx, dataTestId } from "./internal";

const badgeVariants = cva("ui-badge", {
  variants: {
    tone: {
      neutral: "ui-badge-neutral",
      success: "ui-badge-success",
      warning: "ui-badge-warning",
      danger: "ui-badge-destructive",
      destructive: "ui-badge-destructive",
      info: "ui-badge-info",
    },
  },
  defaultVariants: {
    tone: "neutral",
  },
});

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { className, tone, ...props },
  ref,
) {
  return (
    <span
      ref={ref}
      className={cx(badgeVariants({ tone }), className)}
      data-testid={dataTestId(props, "ui-badge")}
      {...props}
    />
  );
});

export function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: React.ReactNode;
  tone?: NonNullable<BadgeProps["tone"]>;
}) {
  return <Badge tone={tone}>{label}</Badge>;
}
