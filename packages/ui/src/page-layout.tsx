import * as React from "react";

import { cx } from "./internal";

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

export function PageHeader({
  actions,
  breadcrumb,
  className,
  description,
  title,
  ...props
}: React.HTMLAttributes<HTMLElement> & {
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  description?: React.ReactNode;
  title: React.ReactNode;
}) {
  return (
    <header className={cx("ui-page-header", className)} {...props}>
      <div className="ui-page-header-copy">
        {breadcrumb ? <div className="ui-page-header-breadcrumb">{breadcrumb}</div> : null}
        <h2 className="ui-page-header-title">{title}</h2>
        {description ? <p className="ui-copy ui-page-header-description">{description}</p> : null}
      </div>
      {actions ? <div className="ui-page-header-actions">{actions}</div> : null}
    </header>
  );
}
