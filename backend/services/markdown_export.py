"""
Markdown export — study notes as a portable .md file (works in Notion,
Obsidian, GitHub, etc.).
"""


def _ts(seconds) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def generate_markdown(job: dict) -> str:
    out: list[str] = []
    add = out.append
    title = job.get("filename") or "Lecture"
    add(f"# Lecture Notes: {title}\n")

    summary = job.get("summary") or {}
    add("## Overview\n")
    add((summary.get("overview") or "_No overview generated._") + "\n")

    if summary.get("key_points"):
        add("## Key Points\n")
        out.extend(f"- {p}" for p in summary["key_points"])
        add("")

    if summary.get("important_concepts"):
        add("## Important Concepts\n")
        out.extend(f"- {c}" for c in summary["important_concepts"])
        add("")

    if job.get("keywords"):
        add("## Keywords\n")
        add(", ".join(f"`{k}`" for k in job["keywords"]) + "\n")

    if job.get("segments"):
        add("## Topics\n")
        for seg in job["segments"]:
            stamp = f" ({_ts(seg.get('start'))})" if seg.get("start") is not None else ""
            add(f"### {seg.get('title', 'Topic')}{stamp}\n")
            add(f"{seg.get('content', '')}\n")

    quiz = job.get("quiz") or {}
    if quiz.get("mcqs") or quiz.get("short_answers"):
        add("## Quiz\n")
        for i, q in enumerate(quiz.get("mcqs") or [], 1):
            add(f"**Q{i}. {q.get('question', '')}** _({q.get('difficulty', '')})_\n")
            options = q.get("options") or []
            for j, opt in enumerate(options):
                add(f"{chr(65 + j)}. {opt}")
            if options:
                add("")
            idx = q.get("answer_index")
            if isinstance(idx, int) and 0 <= idx < len(options):
                answer = f"**Answer:** {chr(65 + idx)}. {options[idx]}"
                if q.get("explanation"):
                    answer += f" — {q['explanation']}"
                add(answer + "\n")
        for i, q in enumerate(quiz.get("short_answers") or [], 1):
            add(f"**Short answer {i}. {q.get('question', '')}**\n")
            if q.get("answer"):
                add(f"> {q['answer']}\n")

    if job.get("flashcards"):
        add("## Flashcards\n")
        add("| Question | Answer |")
        add("|---|---|")
        for fc in job["flashcards"]:
            q = str(fc.get("question", "")).replace("|", "\\|").replace("\n", " ")
            a = str(fc.get("answer", "")).replace("|", "\\|").replace("\n", " ")
            add(f"| {q} | {a} |")
        add("")

    transcript = job.get("cleaned_text") or (job.get("transcript") or {}).get("text", "")
    if transcript:
        add("## Full Transcript\n")
        add(transcript + "\n")

    return "\n".join(out)
