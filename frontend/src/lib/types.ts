export interface Teacher {
  id: string;
  name: string;
  email: string;
}

export interface Prompt {
  id: string;
  teacher_id: string | null;
  title: string;
  category: string;
  activity_type: string;
  body: string;
  is_favorite: boolean;
  is_builtin: boolean;
  created_at: string | null;
  updated_at: string | null;
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

export interface StagePerformance {
  stage_id: string;
  label: string;
  responses: number;
  correct: number;
  incorrect: number;
  completion_rate: number;
  most_common_wrong_answer: string | null;
  most_common_wrong_count: number;
}

export interface InsightsStats {
  students_joined: number;
  participation_rate: number;
  correct_rate: number | null;
  per_stage: StagePerformance[];
  focus_violation_total: number;
  students_locked: number;
  student_stats: {
    student_id: string;
    name: string;
    responses: number;
    correct: number;
    graded: number;
    needs_help: boolean;
    help_requests: number;
    coach_messages: number;
    violations: number;
    locked: boolean;
  }[];
}

export interface Insights {
  source: "ai" | "statistical";
  stats: InsightsStats;
  class_summary: string;
  misconceptions: string[];
  recommendations: string[];
  student_notes: { name: string; note: string }[];
}
