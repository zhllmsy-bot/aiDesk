import * as React from "react";

import { cx } from "./internal";

export const DescriptionList = React.forwardRef<
  HTMLDListElement,
  React.HTMLAttributes<HTMLDListElement>
>(function DescriptionList({ className, ...props }, ref) {
  return <dl ref={ref} className={cx("ui-description-list", className)} {...props} />;
});

export function DescriptionItem({
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

export const KeyValue = DescriptionItem;
