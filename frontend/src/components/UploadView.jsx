import { useId, useRef, useState } from 'react';
import { ArrowRight, CircleAlert, Cpu, FileAudio, HardDrive, UploadCloud, X } from 'lucide-react';
import { asArray, formatBytes, getExtension, isNum, providerLabel } from '../utils';

function normalizeExtensions(list) {
  return asArray(list)
    .filter((e) => typeof e === 'string' && e.trim())
    .map((e) => {
      const ext = e.trim().toLowerCase();
      return ext.startsWith('.') ? ext : `.${ext}`;
    });
}

function validate(file, extensions, maxMb) {
  if (!file) return 'Please choose a file.';
  const ext = getExtension(file.name);
  if (extensions.length && !extensions.includes(ext)) {
    return `"${file.name}" is not a supported format. Please upload one of: ${extensions.join(', ')}.`;
  }
  if (file.size === 0) return 'This file is empty. Please choose a different recording.';
  if (isNum(maxMb) && maxMb > 0 && file.size > maxMb * 1024 * 1024) {
    return `This file is ${formatBytes(file.size)}, which exceeds the ${maxMb} MB upload limit.`;
  }
  return '';
}

export default function UploadView({ config, serverError, onSubmit }) {
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const dragDepth = useRef(0);
  const hintId = useId();
  const errorId = useId();

  const extensions = normalizeExtensions(config?.allowed_extensions);
  const maxMb = isNum(config?.max_upload_mb) ? config.max_upload_mb : null;
  const provider = providerLabel(config?.provider);
  const error = localError || (file ? '' : serverError) || '';

  const pickFile = (candidate) => {
    if (!candidate) return;
    const problem = validate(candidate, extensions, maxMb);
    setLocalError(problem);
    setFile(problem ? null : candidate);
  };

  const openPicker = () => inputRef.current?.click();

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openPicker();
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    dragDepth.current += 1;
    setDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    pickFile(e.dataTransfer?.files?.[0]);
  };

  const handleChange = (e) => {
    pickFile(e.target.files?.[0]);
    e.target.value = '';
  };

  const clearFile = () => {
    setFile(null);
    setLocalError('');
  };

  const formatsLabel = extensions.length
    ? extensions.map((e) => e.slice(1).toUpperCase()).join(', ')
    : 'Common audio formats';

  return (
    <section className="upload-view" aria-labelledby="view-heading">
      <span className="upload-badge">Upload lecture</span>
      <h1 id="view-heading" className="upload-heading" tabIndex={-1}>
        Transform your lectures into smart study notes
      </h1>
      <p className="upload-subtext">
        Upload an audio recording to get a transcript, summary, key topics, a practice quiz and
        flashcards — ready to review or export.
      </p>

      <ul className="upload-meta-pills" aria-label="Upload details">
        <li className="meta-pill">
          <FileAudio size={14} aria-hidden="true" /> {formatsLabel}
        </li>
        {maxMb != null && (
          <li className="meta-pill">
            <HardDrive size={14} aria-hidden="true" /> Up to {maxMb} MB
          </li>
        )}
        {provider && (
          <li className="meta-pill">
            <Cpu size={14} aria-hidden="true" /> {provider}
          </li>
        )}
      </ul>

      <div
        className={`drop-zone ${dragging ? 'is-dragging' : ''} ${error ? 'has-error' : ''}`}
        role="button"
        tabIndex={0}
        aria-describedby={`${hintId}${error ? ` ${errorId}` : ''}`}
        onClick={openPicker}
        onKeyDown={handleKeyDown}
        onDragEnter={handleDragEnter}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="drop-zone-inner">
          <div className="upload-icon-wrap">
            <UploadCloud size={28} aria-hidden="true" />
          </div>
          <span className="drop-zone-title">
            {dragging ? 'Release to select this file' : 'Drop your audio file here'}
          </span>
          <span id={hintId} className="drop-zone-hint">
            or click / press Enter to browse
            {maxMb != null ? ` · max ${maxMb} MB` : ''}
          </span>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="visually-hidden"
          tabIndex={-1}
          aria-hidden="true"
          accept={extensions.length ? extensions.join(',') : 'audio/*'}
          onChange={handleChange}
        />
      </div>

      {error && (
        <p id={errorId} className="form-error" role="alert">
          <CircleAlert size={16} aria-hidden="true" />
          <span>{error}</span>
        </p>
      )}

      {file && (
        <div className="file-selected">
          <div className="file-info">
            <FileAudio size={20} aria-hidden="true" className="file-icon" />
            <div className="file-text">
              <span className="file-name" title={file.name}>{file.name}</span>
              <span className="file-size">{formatBytes(file.size)}</span>
            </div>
            <button
              type="button"
              className="icon-button"
              onClick={clearFile}
              aria-label={`Remove ${file.name}`}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
          <button type="button" className="btn-primary" onClick={() => onSubmit(file)}>
            Process lecture <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      )}
    </section>
  );
}
