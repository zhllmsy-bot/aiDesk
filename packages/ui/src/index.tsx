import * as React from "react";

type Tone = "primary" | "secondary" | "ghost" | "danger";
type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";
type StackGap = "1" | "2" | "3" | "4" | "5" | "6";

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: Tone;
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, tone = "primary", type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx("ui-button", `ui-button-${tone}`, className)}
      {...props}
    />
  );
});

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cx("ui-field", className)} {...props} />;
});

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cx("ui-field", "ui-textarea", className)} {...props} />;
});

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className, ...props }, ref) {
  return <select ref={ref} className={cx("ui-field", className)} {...props} />;
});

export function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: React.ReactNode;
  tone?: BadgeTone;
}) {
  return <span className={cx("ui-badge", `ui-badge-${tone}`)}>{label}</span>;
}

export function Panel({
  eyebrow,
  title,
  actions,
  children,
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="ui-panel">
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
}

export function Stack({
  gap = "4",
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  gap?: StackGap;
}) {
  return <div className={cx("ui-stack", `ui-stack-gap-${gap}`, className)} {...props} />;
}

export function CodeBlock({
  code,
  language,
}: {
  code: string;
  language?: string;
}) {
  return (
    <pre className="ui-code-block" data-language={language}>
      <code>{code}</code>
    </pre>
  );
}
