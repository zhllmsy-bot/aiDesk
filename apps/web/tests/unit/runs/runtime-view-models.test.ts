import { describe, expect, it } from "vitest";

import { getTaskDetailFixture, listRunEvents } from "@/lib/demo-data/runtime-data";
import {
  graphNodeViewModel,
  taskDetailViewModel,
  timelineItemViewModel,
  workflowStatusTone,
} from "@/lib/view-models/runtime-view-models";

describe("runtime view models", () => {
  it("maps raw events to timeline items with readable labels", () => {
    const event = listRunEvents("run_20260419_main")[0];
    expect(event).toBeDefined();
    if (!event) {
      throw new Error("Expected runtime event fixture");
    }
    const item = timelineItemViewModel(event);

    expect(item.label).toBe("Workflow Started");
    expect(item.summary).toContain("Workflow started");
    expect(item.statusTone).toBe("info");
  });

  it("maps waiting approval tasks into highlighted detail state", () => {
    const detail = getTaskDetailFixture("run_20260419_main", "task_patch_guard");
    if (!detail) {
      throw new Error("Expected fixture");
    }

    const viewModel = taskDetailViewModel(detail);

    expect(viewModel.statusTone).toBe("warning");
    expect(viewModel.failureCategoryLabel).toBe("policy gate");
    expect(viewModel.approvalHref).toBe("/review/aprv_patch_guard");
  });

  it("keeps workflow tone mapping stable for critical runtime states", () => {
    expect(workflowStatusTone("waiting_approval")).toBe("warning");
    expect(workflowStatusTone("failed")).toBe("danger");
    expect(workflowStatusTone("completed")).toBe("success");
  });

  it("surfaces subagent todo progress on graph nodes", () => {
    const node = graphNodeViewModel(
      {
        taskId: "task-1",
        title: "Execute focused increment",
        status: "running",
        todoItems: [
          { id: "context", title: "Assemble context", status: "completed" },
          { id: "implement", title: "Apply changes", status: "running" },
        ],
      },
      "run-1",
      "project-1",
    );

    expect(node.todoProgressLabel).toBe("1/2 todo done");
    expect(node.todoItems[1]?.status).toBe("running");
  });
});
