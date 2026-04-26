import * as TabsPrimitive from "@radix-ui/react-tabs";
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

export type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> &
  FieldVariantProps;

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

export type SearchInputProps = InputProps & {
  onClear?: () => void;
};

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  function SearchInput({ className, density, onClear, value, defaultValue, ...props }, ref) {
    const hasValue = value != null ? String(value).length > 0 : defaultValue != null;

    return (
      <div className="ui-search-input">
        <span aria-hidden="true" className="ui-input-icon" />
        <Input
          ref={ref}
          className={cx("ui-search-input-field", className)}
          density={density}
          type="search"
          value={value}
          defaultValue={defaultValue}
          {...props}
        />
        {onClear && hasValue ? (
          <Button
            aria-label="Clear search"
            className="ui-input-clear"
            onClick={onClear}
            size="sm"
            type="button"
            variant="ghost"
          >
            <span aria-hidden="true" className="ui-button-icon">
              x
            </span>
          </Button>
        ) : null}
      </div>
    );
  },
);

export type TextFieldProps = {
  description?: React.ReactNode;
  error?: React.ReactNode;
  inputProps?: InputProps;
  label: React.ReactNode;
};

export function TextField({ description, error, inputProps, label }: TextFieldProps) {
  const generatedId = React.useId();
  const id = inputProps?.id ?? generatedId;
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="ui-text-field">
      <label className="ui-field-label" htmlFor={id}>
        {label}
      </label>
      <Input
        {...inputProps}
        aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
        aria-invalid={Boolean(error) || inputProps?.["aria-invalid"]}
        id={id}
      />
      {description ? (
        <p className="ui-field-description" id={descriptionId}>
          {description}
        </p>
      ) : null}
      {error ? (
        <p className="ui-field-error" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

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

export const Card = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(function Card(
  { className, ...props },
  ref,
) {
  return (
    <section
      ref={ref}
      className={cx("ui-card", className)}
      data-testid={dataTestId(props, "ui-card")}
      {...props}
    />
  );
});

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function CardHeader({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-card-header", className)} {...props} />;
  },
);

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function CardBody({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-card-body", className)} {...props} />;
  },
);

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function CardFooter({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-card-footer", className)} {...props} />;
  },
);

export function Panel({
  eyebrow,
  title,
  actions,
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLElement> & {
  actions?: React.ReactNode;
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
}) {
  return (
    <Card className={cx("ui-panel", className)} {...props}>
      <CardHeader>
        <div>
          {eyebrow ? <div className="ui-eyebrow">{eyebrow}</div> : null}
          <h2 className="ui-panel-title">{title}</h2>
        </div>
        {actions ? <div className="ui-inline-actions">{actions}</div> : null}
      </CardHeader>
      <CardBody>{children}</CardBody>
    </Card>
  );
}

export type SegmentedControlOption = {
  disabled?: boolean;
  label: React.ReactNode;
  value: string;
};

export function SegmentedControl({
  "aria-label": ariaLabel,
  onValueChange,
  options,
  value,
}: {
  "aria-label": string;
  onValueChange: (value: string) => void;
  options: SegmentedControlOption[];
  value: string;
}) {
  return (
    <TabsPrimitive.Root onValueChange={onValueChange} value={value}>
      <TabsPrimitive.List aria-label={ariaLabel} className="ui-segmented-control">
        {options.map((option) => (
          <TabsPrimitive.Trigger
            className="ui-segmented-control-item"
            disabled={option.disabled}
            key={option.value}
            value={option.value}
          >
            {option.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      <div className="ui-segmented-control-panels">
        {options.map((option) => (
          <TabsPrimitive.Content
            className="ui-segmented-control-panel"
            forceMount
            key={option.value}
            value={option.value}
          />
        ))}
      </div>
    </TabsPrimitive.Root>
  );
}

export function StatCard({
  description,
  label,
  value,
}: {
  description?: React.ReactNode;
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <Card className="ui-stat-card">
      <div className="ui-eyebrow">{label}</div>
      <strong>{value}</strong>
      {description ? <p className="ui-copy">{description}</p> : null}
    </Card>
  );
}

export const DescriptionList = React.forwardRef<
  HTMLDListElement,
  React.HTMLAttributes<HTMLDListElement>
>(function DescriptionList({ className, ...props }, ref) {
  return <dl ref={ref} className={cx("ui-description-list", className)} {...props} />;
});

export function KeyValue({
  label,
  value,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <div className="ui-key-value">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export const Avatar = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function Avatar({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-avatar", className)} {...props} />;
  },
);

export const AvatarFallback = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement>
>(function AvatarFallback({ className, ...props }, ref) {
  return <span ref={ref} className={cx("ui-avatar-fallback", className)} {...props} />;
});

export const Breadcrumb = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(
  function Breadcrumb({ className, ...props }, ref) {
    return (
      <nav
        aria-label={props["aria-label"] ?? "Breadcrumbs"}
        ref={ref}
        className={cx("ui-breadcrumb", className)}
        {...props}
      />
    );
  },
);

export const BreadcrumbList = React.forwardRef<
  HTMLOListElement,
  React.OlHTMLAttributes<HTMLOListElement>
>(function BreadcrumbList({ className, ...props }, ref) {
  return <ol ref={ref} className={cx("ui-breadcrumb-list", className)} {...props} />;
});

export const BreadcrumbItem = React.forwardRef<
  HTMLLIElement,
  React.LiHTMLAttributes<HTMLLIElement>
>(function BreadcrumbItem({ className, ...props }, ref) {
  return <li ref={ref} className={cx("ui-breadcrumb-item", className)} {...props} />;
});

export const BreadcrumbLink = React.forwardRef<
  HTMLAnchorElement,
  React.AnchorHTMLAttributes<HTMLAnchorElement>
>(function BreadcrumbLink({ className, ...props }, ref) {
  return <a ref={ref} className={cx("ui-breadcrumb-link", className)} {...props} />;
});

export function BreadcrumbSeparator() {
  return (
    <span aria-hidden="true" className="ui-breadcrumb-separator">
      /
    </span>
  );
}

export const BreadcrumbCurrent = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement>
>(function BreadcrumbCurrent({ className, ...props }, ref) {
  return <span ref={ref} className={cx("ui-breadcrumb-current", className)} {...props} />;
});

export const PageLayout = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    width?: "default" | "wide";
  }
>(function PageLayout({ className, width = "default", ...props }, ref) {
  return (
    <div
      ref={ref}
      className={cx("ui-page-layout", width === "wide" && "ui-page-layout-wide", className)}
      {...props}
    />
  );
});

export const Sidebar = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(
  function Sidebar({ className, ...props }, ref) {
    return <aside ref={ref} className={cx("ui-sidebar", className)} {...props} />;
  },
);

export const SidebarHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SidebarHeader({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-sidebar-header", className)} {...props} />;
  },
);

export const SidebarNav = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(
  function SidebarNav({ className, ...props }, ref) {
    return <nav ref={ref} className={cx("ui-sidebar-nav", className)} {...props} />;
  },
);

export const SidebarFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SidebarFooter({ className, ...props }, ref) {
    return <div ref={ref} className={cx("ui-sidebar-footer", className)} {...props} />;
  },
);

export function SidebarItem({
  active,
  className,
  description,
  label,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  active?: boolean;
  description?: React.ReactNode;
  label: React.ReactNode;
}) {
  return (
    <a
      aria-current={active ? "page" : undefined}
      className={cx("ui-sidebar-item", active && "ui-sidebar-item-active", className)}
      {...props}
    >
      <span className="ui-sidebar-item-label">{label}</span>
      {description ? <span className="ui-sidebar-item-description">{description}</span> : null}
    </a>
  );
}

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
