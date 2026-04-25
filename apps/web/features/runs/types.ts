import type {
  NotificationSummary,
  RunEvent,
  RuntimeBacklogSnapshot,
  TaskAttempt,
  TaskGraphReadModel,
  TimelineReadModel,
  TraceCorrelation,
  WorkerHealthReadModel,
  WorkflowName,
  WorkflowRunStatus,
} from "@ai-desk/contracts-runtime";

export interface RunRecord {
  id: string;
  projectId: string;
  projectName: string;
  workflowName: WorkflowName | string;
  workflowStatus: WorkflowRunStatus;
  startedAt: string;
  updatedAt: string;
  statusReason?: string | null;
  currentTaskId?: string | null;
  currentTaskTitle?: string | null;
  waitingForApproval?: boolean;
  approvalId?: string | null;
}

export interface TaskDetailRecord {
  runId: string;
  taskId: string;
  projectId: string;
  title: string;
  description: string;
  executor: string;
  status: string;
  acceptanceCriteria: string[];
  verificationSummary: string;
  verificationStatus: "passed" | "failed" | "warning";
  retryCount: number;
  failureCategory: string | null;
  failureReason: string | null;
  waitingApprovalReason: string | null;
  blockedReason: string | null;
  linkedArtifactIds: string[];
  approvalId: string | null;
}

export interface RuntimeDataset {
  run: RunRecord;
  events: RunEvent[];
  timeline: TimelineReadModel;
  graph: TaskGraphReadModel;
  attemptsByTaskId: Record<string, TaskAttempt[]>;
  taskDetails: Record<string, TaskDetailRecord>;
  trace: TraceCorrelation;
  notifications: NotificationSummary[];
  workers: WorkerHealthReadModel[];
  backlog: RuntimeBacklogSnapshot;
}
