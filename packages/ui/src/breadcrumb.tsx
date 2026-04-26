import * as React from "react";

import { cx } from "./internal";

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
