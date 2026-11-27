import { Component } from 'react';
import { CircleAlert } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Rendering error:', error, info?.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false });
    this.props.onReset?.();
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <section className="state-view" role="alert">
        <div className="state-icon state-icon--error">
          <CircleAlert size={32} aria-hidden="true" />
        </div>
        <h1 className="state-title">Something went wrong displaying this page</h1>
        <p className="state-text">
          An unexpected problem occurred. You can start over with a new upload.
        </p>
        <div className="state-actions">
          <button type="button" className="btn-primary" onClick={this.handleReset}>
            Start over
          </button>
        </div>
      </section>
    );
  }
}
