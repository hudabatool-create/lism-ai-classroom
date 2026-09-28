/**
 * LISM's own words on the student's screen, in the language of the lesson.
 *
 * The activity itself is written in whatever language the teacher chose, but
 * the strip LISM wraps around it was always English. An Arabic lesson inside
 * an English frame -- "10 marks", "left", "Response submitted" -- reads as
 * half-finished to the teacher it was built for, and that teacher is most of
 * this school.
 *
 * Only the student's screen is translated here. The teacher's dashboard stays
 * in English deliberately: a teacher chose their own interface language when
 * they signed up, and their screen does not change from lesson to lesson.
 */
export type LessonLang = "en" | "ar";

const EN = {
  joinTitle: "Enter your details to join.",
  name: "Name",
  grade: "Grade",
  section: "Section",
  join: "Join Activity",
  joining: "Joining...",
  waitingTitle: "Waiting for your teacher",
  waitingFirst: "The lesson will appear here as soon as your teacher starts the first section.",
  waitingNext: "That section is finished. Your teacher will start the next one shortly.",
  marksBanner: (marks: number) => `${marks} marks — your teacher will see and review this`,
  noMarks: "No marks — your teacher will see this",
  timeLeft: "left",
  pausedByTeacher: "paused by your teacher",
  timesUpShort: "time's up — wait for your teacher",
  timesUpBanner: "⏰ Time's Up! Please stop working and wait for your teacher's instructions.",
  welcomeBack: "Welcome back — you're back in the same lesson",
  answersSaved: (n: number) => `, with your ${n} answer${n === 1 ? "" : "s"} saved`,
  connected: "You're connected. Nothing else to do — just wait.",
  assessmentNotice:
    "This is an assessment. Leaving this window will be recorded, and repeated exits will lock your activity.",
  submitted: "Response submitted — your teacher can see it live.",
  sentToTeacher: "Answer sent to your teacher.",
  couldNotSubmit: "Could not submit your answer.",
  lessonEnded: "Your teacher ended the lesson.",
  unlocked: "Your teacher has unlocked your screen — you can carry on.",
  copyBlocked: "Copy and paste are switched off for this lesson — please type your answer.",
  needHelp: "Need help?",
  coach: "AI Learning Coach",
  coachAsk: "Ask the coach...",
  coachTyping: "Coach is typing...",
  helpSent: "Your teacher has been notified",
  paused: "Paused by your teacher",
  sectionsCompleted: "Sections completed",
  yourScore: "Your score",
  marksSoFar: "Marks so far",
  notScored: "Not scored",
  timeSpent: "Time spent",
  sessionNotFound: "Session not found",
  couldNotJoin: "Could not join",
  finalWarning: "Final warning: one more exit will lock this activity.",
  warning: "Warning: leaving this window during an assessment is being recorded.",
  locked:
    "This activity has been locked because you exceeded the maximum number of window exits. Your teacher has been notified.",
};

const AR: typeof EN = {
  joinTitle: "أدخل بياناتك للانضمام.",
  name: "الاسم",
  grade: "الصف",
  section: "الشعبة",
  join: "انضم إلى النشاط",
  joining: "جارٍ الانضمام…",
  waitingTitle: "في انتظار معلمك",
  waitingFirst: "سيظهر الدرس هنا فور أن يبدأ معلمك القسم الأول.",
  waitingNext: "انتهى هذا القسم. سيبدأ معلمك القسم التالي بعد قليل.",
  marksBanner: (marks: number) => `${marks} درجات — سيطّلع معلمك على إجابتك ويراجعها`,
  noMarks: "بلا درجات — سيطّلع معلمك على إجابتك",
  timeLeft: "متبقٍ",
  pausedByTeacher: "أوقفه معلمك مؤقتًا",
  timesUpShort: "انتهى الوقت — انتظر معلمك",
  timesUpBanner: "⏰ انتهى الوقت! توقف عن العمل وانتظر تعليمات معلمك.",
  welcomeBack: "أهلًا بعودتك — أنت في الدرس نفسه",
  answersSaved: (n: number) => ` مع حفظ ${n} من إجاباتك`,
  connected: "أنت متصل. لا شيء عليك سوى الانتظار.",
  assessmentNotice:
    "هذا تقييم. سيُسجل خروجك من هذه النافذة، وتكراره يقفل النشاط.",
  submitted: "تم إرسال إجابتك — يستطيع معلمك رؤيتها الآن.",
  sentToTeacher: "أُرسلت إجابتك إلى معلمك.",
  couldNotSubmit: "تعذّر إرسال إجابتك.",
  lessonEnded: "أنهى معلمك الدرس.",
  unlocked: "فتح معلمك شاشتك — يمكنك المتابعة.",
  copyBlocked: "النسخ واللصق معطّلان في هذا الدرس — اكتب إجابتك بنفسك.",
  needHelp: "أحتاج مساعدة",
  coach: "مدرّب التعلّم",
  coachAsk: "اسأل المدرّب…",
  coachTyping: "المدرّب يكتب…",
  helpSent: "تم إبلاغ معلمك",
  paused: "أوقف معلمك الدرس مؤقتًا",
  sectionsCompleted: "الأقسام المكتملة",
  yourScore: "درجتك",
  marksSoFar: "الدرجات حتى الآن",
  notScored: "لم تُصحَّح بعد",
  timeSpent: "الوقت المستغرق",
  sessionNotFound: "لم يتم العثور على الجلسة",
  couldNotJoin: "تعذّر الانضمام",
  finalWarning: "تحذير أخير: خروج آخر سيقفل هذا النشاط.",
  warning: "تنبيه: يتم تسجيل خروجك من النافذة أثناء التقييم.",
  locked: "أُقفل هذا النشاط لتجاوزك العدد المسموح به للخروج من النافذة. وقد أُبلغ معلمك.",
};

/** The lesson's own language, defaulting to English when it does not say. */
export function lessonLang(manifest: { lang?: string | null } | null | undefined): LessonLang {
  return manifest?.lang === "ar" ? "ar" : "en";
}

export function lessonDir(manifest: { dir?: string | null } | null | undefined): "rtl" | "ltr" {
  return manifest?.dir === "rtl" ? "rtl" : "ltr";
}

export function strings(lang: LessonLang) {
  return lang === "ar" ? AR : EN;
}
