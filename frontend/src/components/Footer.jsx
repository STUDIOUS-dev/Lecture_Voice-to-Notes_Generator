export default function Footer() {
  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <span className="footer-brand">
          <span className="footer-logo" aria-hidden="true">IL</span>
          IntelliLecture
        </span>
        <span className="footer-text">
          Turn recorded lectures into transcripts, summaries, quizzes and flashcards.
        </span>
        <span className="footer-text">© {new Date().getFullYear()}</span>
      </div>
    </footer>
  );
}
