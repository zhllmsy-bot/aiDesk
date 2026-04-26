import * as React from "react";

import { cx } from "./internal";

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

export function SidebarGroup({
  className,
  label,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  label?: React.ReactNode;
}) {
  return (
    <div className={cx("ui-sidebar-group", className)} {...props}>
      {label ? <div className="ui-sidebar-group-label">{label}</div> : null}
      <div className="ui-sidebar-group-body">{props.children}</div>
    </div>
  );
}

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
