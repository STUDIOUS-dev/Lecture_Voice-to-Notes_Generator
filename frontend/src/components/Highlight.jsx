/** Renders text with every match of `regex` (which must have one capture group) wrapped in <mark>. */
export default function Highlight({ text, regex }) {
  if (!regex || !text) return text || null;
  const parts = text.split(regex);
  return parts.map((part, i) =>
    i % 2 === 1 ? <mark key={i}>{part}</mark> : part,
  );
}
