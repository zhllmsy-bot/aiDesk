import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { Button } from "./button";
import { cx, dataTestId } from "./internal";

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
  clearLabel?: string;
  icon?: React.ReactNode;
  onClear?: () => void;
};

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  function SearchInput(
    {
      className,
      clearLabel = "Clear search",
      density,
      icon,
      onClear,
      value,
      defaultValue,
      ...props
    },
    ref,
  ) {
    const hasValue = value != null ? String(value).length > 0 : defaultValue != null;

    return (
      <div className="ui-search-input">
        <span aria-hidden="true" className="ui-input-icon">
          {icon}
        </span>
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
            aria-label={clearLabel}
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
