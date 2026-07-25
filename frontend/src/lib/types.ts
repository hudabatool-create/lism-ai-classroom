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

export interface SessionInfo {
  id: string;
  teacher_id: string;
  activity_id: string;
  code: string;
  status: "active" | "ended";
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
