import * as React from "react";

import { cx } from "./internal";

export const CodeBlock = React.forwardRef<
  HTMLPreElement,
  React.HTMLAttributes<HTMLPreElement> & {
    code: string;
    language?: string;
  }
>(function CodeBlock({ code, language, className, ...props }, ref) {
  return (
    <pre
      ref={ref}
      aria-label={props["aria-label"] ?? `${language ?? "text"} code block`}
      className={cx("ui-code-block", className)}
      data-language={language}
      tabIndex={props.tabIndex ?? 0}
      {...props}
    >
      <code>{code}</code>
    </pre>
  );
});
