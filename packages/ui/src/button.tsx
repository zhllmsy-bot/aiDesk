import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cx, dataTestId } from "./internal";

export const buttonVariants = cva("ui-button", {
  variants: {
    variant: {
      primary: "ui-button-primary",
      secondary: "ui-button-secondary",
      ghost: "ui-button-ghost",
      destructive: "ui-button-destructive",
      danger: "ui-button-destructive",
      outline: "ui-button-outline",
      link: "ui-button-link",
    },
    size: {
      sm: "ui-button-sm",
      md: "ui-button-md",
      lg: "ui-button-lg",
    },
  },
  defaultVariants: {
    variant: "primary",
    size: "md",
  },
});

export type ButtonProps = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "color"> &
  VariantProps<typeof buttonVariants> & {
    tone?: VariantProps<typeof buttonVariants>["variant"];
  };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, tone, size, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(buttonVariants({ variant: variant ?? tone, size }), className)}
      data-testid={dataTestId(props, "ui-button")}
      {...props}
    />
  );
});

export type ButtonLinkProps = React.AnchorHTMLAttributes<HTMLAnchorElement> &
  VariantProps<typeof buttonVariants> & {
    tone?: VariantProps<typeof buttonVariants>["variant"];
  };

export const ButtonLink = React.forwardRef<HTMLAnchorElement, ButtonLinkProps>(function ButtonLink(
  { className, variant, tone, size, ...props },
  ref,
) {
  return (
    <a
      ref={ref}
      className={cx(buttonVariants({ variant: variant ?? tone, size }), className)}
      data-testid={dataTestId(props, "ui-button-link")}
      {...props}
    />
  );
});
