/** Longest mailto: link most mail apps handle before they start cutting the body. */
export const MAILTO_SAFE_LENGTH = 2000;

/**
 * Builds a mailto: link with the recipient, subject and body filled in.
 * The subject becomes "Re: ..." unless it already starts that way.
 */
export function mailtoUrl(item: { email: string; subject: string }, body: string): string {
  const subject = item.subject.trim();
  const reSubject = !subject ? "Re: your message" : /^re:/i.test(subject) ? subject : `Re: ${subject}`;
  const to = encodeURIComponent(item.email.trim()).replace(/%40/g, "@");
  // RFC 6068 wants CRLF line breaks inside the body.
  const text = body.replace(/\r?\n/g, "\r\n");
  return `mailto:${to}?subject=${encodeURIComponent(reSubject)}&body=${encodeURIComponent(text)}`;
}
