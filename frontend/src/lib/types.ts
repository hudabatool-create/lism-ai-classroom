export interface Teacher {
  id: string;
  name: string;
  email: string;
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
  correct: boolean | null;
  answer: string;
  submitted_at: string;
}
