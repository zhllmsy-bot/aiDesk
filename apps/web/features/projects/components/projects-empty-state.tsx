import Link from "next/link";

import { Button } from "@ai-desk/ui";

export function ProjectsEmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: { label: string; href: string };
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p className="ui-copy">{description}</p>
      {action ? (
        <Link href={action.href}>
          <Button tone="secondary">{action.label}</Button>
        </Link>
      ) : null}
    </div>
  );
}
