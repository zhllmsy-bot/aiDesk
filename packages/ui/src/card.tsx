import * as React from "react";

import { cx, dataTestId } from "./internal";

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
