import type * as React from "react";

import { Card } from "./card";

export function StatCard({
  description,
  label,
  trend,
  value,
}: {
  description?: React.ReactNode;
  label: React.ReactNode;
  trend?: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <Card className="ui-stat-card">
      <div className="ui-stat-card-header">
        <div className="ui-eyebrow">{label}</div>
        {trend ? <div className="ui-stat-card-trend">{trend}</div> : null}
      </div>
      <strong>{value}</strong>
      {description ? <p className="ui-copy">{description}</p> : null}
    </Card>
  );
}
