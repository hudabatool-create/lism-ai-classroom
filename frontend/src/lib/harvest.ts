/**
 * Reads what the student actually wrote, when the activity won't tell us.
 *
 * LISM's response contract asks an activity to post its answers back. Every
 * activity built from a LISM master prompt does. Plenty of real ones do not:
 * a worksheet a teacher generated elsewhere validates the answer, prints
 * "Answer accepted!", and reports nothing. The student sees success, the
 * teacher's live feed stays empty, and neither has any way to tell why.
 *
 * That is the same problem lockstep had, and it has the same answer: the
 * activity is served from LISM's own origin, so we can stop asking. This reads
 * the answer fields in the section the teacher started and reports them
 * ourselves.
 *
 * What it deliberately does NOT do is decide whether the answer is right.
 * Nothing here can know that, and a guess dressed up as a mark is worse than
 * no mark: it is reported as awaiting the teacher, which is the truth.
 */

/** Fields a student types an answer into. */
const ANSWER_FIELDS = [
  "textarea",
  "input[type='text']",
  "input[type='number']",
  "input[type='search']",
  "input:not([type])",
  "select",
  "input[type='radio']:checked",
  "input[type='checkbox']:checked",
  "[contenteditable='true']",
].join(",");

/** A control that means "I am done with this answer".
 *
 * English-only matching meant no Arabic lesson ever reported anything. A
 * Grade 5 Arabic deck's button reads "إرسال" — send — and nothing here
 * recognised it, so the teacher's panel sat on "0 of 1 answered" for a class
 * that had answered everything. In a bilingual school that is not an edge
 * case, it is half the timetable.
 */
const SUBMIT_TEXT = /\b(submit|check|done|finish(ed)?|save|answer|mark it|complete)\b/i;

/**
 * The same idea in the other languages this school teaches in.
 *
 * Matched as plain substrings rather than with \b, because JavaScript word
 * boundaries are defined on Latin word characters and never fire in Arabic.
 */
const SUBMIT_WORDS_INTL = [
  // Send / check / hand in
  "إرسال", "أرسل", "ارسال", "تحقق", "تأكيد", "سلّم", "تسليم",   // Arabic
  // Save / record. A reflection is saved, not sent -- an Arabic deck ended
  // its lesson on "حفظ التأمل", and that one word was the difference between
  // a teacher seeing thirty reflections and seeing none. Every other stage
  // in the same deck said إرسال and reported perfectly.
  "حفظ", "احفظ", "سجل", "سجّل",                                // Arabic
  "جمع کریں", "بھیجیں", "محفوظ کریں",                           // Urdu
  "envoyer", "soumettre", "vérifier", "valider",               // French
  "enregistrer", "sauvegarder",                                // French
  "enviar", "comprobar", "entregar", "guardar",                // Spanish
];

function looksLikeSubmit(text: string): boolean {
  if (SUBMIT_TEXT.test(text)) return true;
  const lower = text.toLowerCase();
  return SUBMIT_WORDS_INTL.some((word) => lower.includes(word));
}

/** Fields that identify the student rather than answer anything. */
const IDENTITY = /\b(name|class|section|date|student|roll|id)\b/i;

export interface HarvestedAnswer {
  /** Human-readable, ready to show a teacher. */
  text: string;
  /** How many fields the student actually filled in. */
  filled: number;
}

function labelFor(el: HTMLElement, doc: Document): string {
  const id = el.getAttribute("id");
  if (id) {
    const label = doc.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (label?.textContent?.trim()) return label.textContent.trim();
  }
  const wrapping = el.closest("label");
  if (wrapping?.textContent?.trim()) return wrapping.textContent.trim();
  // The nearest preceding label in the same field group -- the shape almost
  // every generated worksheet uses.
  const group = el.closest(".input-group, .question, .field, div");
  const near = group?.querySelector("label, .input-label, .question-label");
  if (near?.textContent?.trim()) return near.textContent.trim();
  return el.getAttribute("placeholder")?.trim() || "";
}

function valueOf(el: Element): string {
  // Matched on tagName rather than `instanceof`. The activity lives in an
  // iframe, so its elements come from that frame's realm and are not
  // instances of this window's HTMLSelectElement at all -- every check would
  // silently take the wrong branch, and a select would report as raw text.
  const tag = el.tagName.toUpperCase();

  if (tag === "SELECT") {
    const select = el as HTMLSelectElement;
    return select.selectedOptions?.[0]?.textContent?.trim() || select.value.trim();
  }

  if (tag === "INPUT") {
    const input = el as HTMLInputElement;
    if (input.type === "radio" || input.type === "checkbox") {
      // The visible choice, not the machine value: "Photosynthesis", not "b".
      const label = input.closest("label")?.textContent?.trim();
      return label || input.value.trim();
    }
    return input.value.trim();
  }

  if (tag === "TEXTAREA") return (el as HTMLTextAreaElement).value.trim();

  const host = el as HTMLElement;
  return (host.innerText ?? host.textContent ?? "").trim();
}

/**
 * Everything the student has written in this section, as one readable answer.
 *
 * Each field is labelled with its own question, because a teacher scanning a
 * live feed needs to know which answer they are looking at -- three bare lines
 * of code with no prompts attached tells them almost nothing.
 */
export function collectAnswers(section: HTMLElement, doc: Document): HarvestedAnswer {
  const parts: string[] = [];
  let filled = 0;

  section.querySelectorAll<HTMLElement>(ANSWER_FIELDS).forEach((el) => {
    // Hidden fields belong to a part of the activity the student cannot see.
    if (el.offsetParent === null && el.getAttribute("type") !== "radio") return;
    const value = valueOf(el);
    if (!value) return;

    const label = labelFor(el, doc);
    // A worksheet's own name/class/date header is not an answer, and copying
    // it into the response feed would put the student's details where they
    // do not belong.
    if (IDENTITY.test(label) && value.length < 40 && !el.matches("textarea")) return;

    filled += 1;
    const question = label.replace(/\s+/g, " ").slice(0, 120);
    // A radio wrapped in its own label gives the same text twice, so a
    // multiple-choice answer read "C) <p style="red"> → C) <p style="red">"
    // all down the teacher's feed. The option is the answer; there is no
    // question to pair it with here.
    const same = question && value.startsWith(question.slice(0, 40));
    parts.push(question && !same ? `${question} → ${value}` : value);
  });

  return { text: parts.join("\n\n").slice(0, 4000), filled };
}

/**
 * Calls back when the student presses this section's submit button.
 *
 * Capture phase, so it still fires for an activity that stops the event on its
 * own handler. It only observes -- the activity's own validation, model-answer
 * unlocking and scoring all still run exactly as they would standalone.
 */
export function watchSubmits(doc: Document, onSubmit: () => void): () => void {
  const handler = (event: Event) => {
    const target = event.target as HTMLElement | null;
    const control = target?.closest("button, input[type='submit'], [role='button']");
    if (!control) return;
    const text = (control.textContent ?? (control as HTMLInputElement).value ?? "").trim();
    if (text.length > 40 || !looksLikeSubmit(text)) return;
    // After the activity's own handler, so anything it writes into the page
    // (a normalised value, a computed score) is already there to be read.
    setTimeout(onSubmit, 0);
  };
  doc.addEventListener("click", handler, true);
  return () => doc.removeEventListener("click", handler, true);
}
