import { Suspense } from "react";

import { ProjectsIndexScreen } from "@/features/projects/components/projects-index-screen";

export default function ProjectsPage() {
  return (
    <Suspense fallback={<div className="surface-note">Loading project filters...</div>}>
      <ProjectsIndexScreen />
    </Suspense>
  );
}
