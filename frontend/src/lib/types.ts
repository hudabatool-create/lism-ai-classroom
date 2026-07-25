export interface Teacher {
  id: string;
  name: string;
  email: string;
}

export interface Stage {
  id: string;
  label: string;
  type: string;
  durationSeconds: number;
  sequentialLock: boolean;
  marks?: unknown;
}

export interface LessonManifest {
  managed: boolean;
  lessonType: string;
  subject: string;
  grade: string;
  week: string;
  topic: string;
  learningObjectives: Record<string, string>;
  keywords: string[];
  dok: { level: number; label: string; marks: number }[];
  deliveryMode: string;
  sessionType: string;
  stages: Stage[];
}

export interface Activity {
  id: string;
  teacher_id: string;
  title: string;
  subject: string;
  grade: string;
  activity_type: string;
  source: "upload" | "ai";
  created_at: string;
  manifest: LessonManifest;
}

export type SessionType = "lesson" | "practice" | "assessment";

export interface SessionInfo {
  id: string;
  teacher_id: string;
  activity_id: string;
  code: string;
  status: "active" | "ended";
  session_type: SessionType;
  created_at: string;
  ended_at: string | null;
  join_url?: string;
  current_stage_index: number;
  stage_status: "idle" | "running" | "ended";
  stage_started_at: string | null;
  stage_duration_seconds: number | null;
}

export interface Student {
  id: string;
  session_id: string;
  name: string;
  grade: string;
  section: string;
  joined_at: string;
  needs_help: boolean;
  help_requests: number;
}

export interface ResponseItem {
  id: string;
  session_id: string;
  student_id: string;
  stage_id: string;
  correct: boolean | null;
  answer: string;
  mark: number | null;
  submitted_at: string;
}

export type StudentStatusValue = "locked" | "inactive" | "needs_help" | "completed" | "working" | "waiting";

export interface StudentStatus {
  status: StudentStatusValue;
  violation_count: number;
  help_requests: number;
}

export interface FocusViolation {
  id: string;
  session_id: string;
  student_id: string;
  type: string;
  violation_number: number;
  occurred_at: string;
}
