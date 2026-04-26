import * as React from "react";

import { cx } from "./internal";

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
