import * as TabsPrimitive from "@radix-ui/react-tabs";
import type * as React from "react";

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
