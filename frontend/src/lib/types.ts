export interface Teacher {
  id: string;
  name: string;
  email: string;
  email_verified: boolean;
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
  /** Total the stage is worth. null when it is deliberately unmarked. */
  marks: number | null;
  /** The portion the activity can score itself; the rest is the teacher's. */
  autoMarks: number | null;
  teacherMarks: number | null;
  rubric: RubricCriterion[];
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
  asset_files: string[];
  /** Set only on the generate response: explains when a starter template was
   *  used instead of AI-written content, and why. */
  warning?: string | null;
}

export interface ActivityDetail extends Activity {
  html: string;
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
  stage_status: "idle" | "running" | "paused" | "ended";
  stage_started_at: string | null;
  // While running, the time left from stage_started_at. Pausing rewrites this
  // to the remaining seconds, so the same countdown maths works either way.
  stage_duration_seconds: number | null;
  copy_paste_protection: boolean;
  focus_monitoring: boolean;
  max_warnings: number;
  timer_sound: "none" | "chime" | "bell" | "school_bell";
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

/** One stage's marks for one student, as computed by the backend's scoring module. */
export interface StageScore {
  stage_id: string;
  label: string;
  marks: number | null;
  auto_marks: number | null;
  teacher_marks: number | null;
  answered: boolean;
  answer: string;
  correct: boolean | null;
  auto_awarded: number | null;
  teacher_awarded: number | null;
  teacher_feedback: string | null;
  awarded: number | null;
  pending: number;
  status: "unmarked" | "not_answered" | "auto_graded" | "pending_review" | "teacher_graded";
}

export interface StudentMarks {
  student_id: string;
  name: string;
  grade: string;
  section: string;
  stages: StageScore[];
  max_score: number | null;
  auto_scored: number | null;
  teacher_scored: number | null;
  awarded_total: number | null;
  pending_review: number | null;
  not_attempted: number | null;
  fully_graded: boolean;
}

export interface RubricCriterion {
  label: string;
  marks: number;
  descriptor: string;
  objective: boolean;
}

export interface SessionMarks {
  activity_title: string;
  session_code: string;
  total_marks: number | null;
  stages: {
    id: string;
    label: string;
    marks: number;
    auto_marks: number | null;
    teacher_marks: number | null;
    rubric: RubricCriterion[];
  }[];
  students: StudentMarks[];
  awaiting_review: number;
}
