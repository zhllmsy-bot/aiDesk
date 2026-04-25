import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

type StackGap = "1" | "2" | "3" | "4" | "5" | "6";
type TestIdProps = {
  "data-testid"?: string;
};

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function dataTestId(props: object, fallback: string) {
  return (props as TestIdProps)["data-testid"] ?? fallback;
}

const buttonVariants = cva("ui-button", {
  variants: {
    tone: {
      primary: "ui-button-primary",
      secondary: "ui-button-secondary",
      ghost: "ui-button-ghost",
      danger: "ui-button-danger",
    },
  },
  defaultVariants: {
    tone: "primary",
  },
});

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, tone, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(buttonVariants({ tone }), className)}
      data-testid={dataTestId(props, "ui-button")}
      {...props}
    />
  );
});

const fieldVariants = cva("ui-field", {
  variants: {
    density: {
      default: "ui-field-default",
      compact: "ui-field-compact",
    },
  },
  defaultVariants: {
    density: "default",
  },
});

type FieldVariantProps = VariantProps<typeof fieldVariants>;

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & FieldVariantProps;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, density, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cx(fieldVariants({ density }), className)}
      data-testid={dataTestId(props, "ui-input")}
      {...props}
    />
  );
});

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & FieldVariantProps;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, density, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cx(fieldVariants({ density }), "ui-textarea", className)}
      data-testid={dataTestId(props, "ui-textarea")}
      {...props}
    />
  );
});

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & FieldVariantProps;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, density, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cx(fieldVariants({ density }), "ui-select", className)}
      data-testid={dataTestId(props, "ui-select")}
      {...props}
    />
  );
});

const badgeVariants = cva("ui-badge", {
  variants: {
    tone: {
      neutral: "ui-badge-neutral",
      success: "ui-badge-success",
      warning: "ui-badge-warning",
      danger: "ui-badge-danger",
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

export const Panel = React.forwardRef<
  HTMLElement,
  React.HTMLAttributes<HTMLElement> & {
    eyebrow?: React.ReactNode;
    title: React.ReactNode;
    actions?: React.ReactNode;
  }
>(function Panel({ eyebrow, title, actions, children, className, ...props }, ref) {
  return (
    <section ref={ref} className={cx("ui-panel", className)} {...props}>
      <div className="ui-panel-header">
        <div>
          {eyebrow ? <div className="ui-eyebrow">{eyebrow}</div> : null}
          <h2 className="ui-panel-title">{title}</h2>
        </div>
        {actions ? <div className="inline-actions">{actions}</div> : null}
      </div>
      <div className="ui-panel-body">{children}</div>
    </section>
  );
});

export const Stack = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    gap?: StackGap;
  }
>(function Stack({ gap = "4", className, ...props }, ref) {
  return <div ref={ref} className={cx("ui-stack", `ui-stack-gap-${gap}`, className)} {...props} />;
});

export const CodeBlock = React.forwardRef<
  HTMLPreElement,
  React.HTMLAttributes<HTMLPreElement> & {
    code: string;
    language?: string;
  }
>(function CodeBlock({ code, language, className, ...props }, ref) {
  return (
    <pre ref={ref} className={cx("ui-code-block", className)} data-language={language} {...props}>
      <code>{code}</code>
    </pre>
  );
});

export const Table = React.forwardRef<
  HTMLTableElement,
  React.TableHTMLAttributes<HTMLTableElement>
>(function Table({ className, ...props }, ref) {
  return <table ref={ref} className={cx("ui-table", className)} {...props} />;
});

export const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(function TableHeader({ className, ...props }, ref) {
  return <thead ref={ref} className={className} {...props} />;
});

export const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(function TableBody({ className, ...props }, ref) {
  return <tbody ref={ref} className={className} {...props} />;
});

export const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(function TableRow({ className, ...props }, ref) {
  return <tr ref={ref} className={className} {...props} />;
});

export const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(function TableHead({ className, ...props }, ref) {
  return <th ref={ref} className={className} {...props} />;
});

export const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(function TableCell({ className, ...props }, ref) {
  return <td ref={ref} className={className} {...props} />;
});
