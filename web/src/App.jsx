import React, { useMemo, useRef, useState } from 'react';

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const STATUS = {
  idle: 'idle',
  loading: 'loading',
  success: 'success',
  error: 'error',
};

export default function App() {
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [status, setStatus] = useState(STATUS.idle);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [notifyStatus, setNotifyStatus] = useState('idle');
  const [notifyMessage, setNotifyMessage] = useState('');

  const galleryInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const frameClass = useMemo(() => {
    if (!result) return 'frame frame-idle';
    if (result.label === 1) return 'frame frame-danger';
    if (result.label === 0) return 'frame frame-clear';
    return 'frame frame-idle';
  }, [result]);

  const handlePickFile = (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    setImageFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError('');
    setStatus(STATUS.idle);
  };

  const onPickGallery = () => {
    galleryInputRef.current?.click();
  };

  const onPickCamera = () => {
    cameraInputRef.current?.click();
  };

  const analyzeImage = async () => {
    if (!imageFile) return;

    setStatus(STATUS.loading);
    setError('');
    setResult(null);
    setNotifyStatus('idle');
    setNotifyMessage('');

    const formData = new FormData();
    formData.append('file', imageFile, imageFile.name || 'image.jpg');

    try {
      const response = await fetch(`${BASE_URL}/predict`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to reach backend.');
      }

      const data = await response.json();
      const label = typeof data.label === 'number' ? data.label : data.result;

      setResult({
        label: Number(label),
        message: data.message || (Number(label) === 1 ? 'DMC Action Required' : 'No Action Required'),
      });
      setStatus(STATUS.success);
    } catch (err) {
      setStatus(STATUS.error);
      setError('Could not reach server. Make sure backend is running and IP is correct.');
    }
  };

  const requestLocation = () => {
    if (!navigator.geolocation) {
      setNotifyStatus('error');
      setNotifyMessage('Geolocation is not supported in this browser.');
      return;
    }

    setNotifyStatus('sending');
    setNotifyMessage('Requesting GPS permission...');

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const payload = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
          label: result?.label ?? null,
          timestamp: new Date().toISOString(),
        };

        try {
          const response = await fetch(`${BASE_URL}/notify`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          });

          if (!response.ok) {
            throw new Error('Notify failed');
          }

          setNotifyStatus('sent');
          setNotifyMessage('Location shared with BlackBox response team.');
        } catch (err) {
          setNotifyStatus('error');
          setNotifyMessage('Could not send location to backend.');
        }
      },
      (geoError) => {
        setNotifyStatus('error');
        if (geoError.code === 1) {
          setNotifyMessage('Permission denied. Please allow location access.');
        } else {
          setNotifyMessage('Unable to get GPS location.');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  };

  return (
    <div className="page">
      <div className="glow" />
      <header className="header">
        <div className="brand">BlackBox</div>
        <div className="tagline">Garbage Detection, distilled to a single signal.</div>
      </header>

      <main className="layout">
        <section className="panel">
          <div className={frameClass}>
            {previewUrl ? (
              <img src={previewUrl} alt="Selected" className="preview" />
            ) : (
              <div className="placeholder">
                <div className="placeholder-title">No image selected</div>
                <div className="placeholder-sub">Upload or capture to begin analysis.</div>
              </div>
            )}
          </div>

          <div className="controls">
            <button className="button button-primary" onClick={onPickCamera}>
              Capture Image
            </button>
            <button className="button button-outline" onClick={onPickGallery}>
              Upload From Gallery
            </button>
          </div>

          <div className="actions">
            {imageFile && (
              <button
                className="button button-analyze"
                onClick={analyzeImage}
                disabled={status === STATUS.loading}
              >
                {status === STATUS.loading ? 'Analyzing...' : 'Analyze'}
              </button>
            )}
          </div>

          {status === STATUS.error && <div className="error">{error}</div>}
        </section>

        <section className="panel panel-results">
          <div className="result-header">Pipeline Output</div>
          <div className={`result-card ${result?.label === 1 ? 'result-danger' : result?.label === 0 ? 'result-clear' : ''}`}>
            <div className="result-title">
              {result?.label === 1
                ? 'DMC Action Required'
                : result?.label === 0
                ? 'No Action Required'
                : 'Awaiting Analysis'}
            </div>
            <div className="result-subtitle">
              {result?.label === 1
                ? 'Garbage detected. Notify the response team immediately.'
                : result?.label === 0
                ? 'Scene is clean. No action is required.'
                : 'Upload an image to activate the detection pipeline.'}
            </div>
            <div className="result-signal">
              <div className={`signal-dot ${result?.label === 1 ? 'signal-danger' : result?.label === 0 ? 'signal-clear' : ''}`} />
              <span>{result?.label === 1 ? 'Critical' : result?.label === 0 ? 'Stable' : 'Standby'}</span>
            </div>
          </div>

          {result?.label === 1 && (
            <div className="notify">
              <div className="notify-title">Share location with DMC</div>
              <div className="notify-subtitle">Send GPS coordinates to the BlackBox response team.</div>
              <button
                className="button button-danger"
                onClick={requestLocation}
                disabled={notifyStatus === 'sending'}
              >
                {notifyStatus === 'sending' ? 'Sending location...' : 'Share Location'}
              </button>
              {notifyMessage && (
                <div className={`notify-message ${notifyStatus}`}>{notifyMessage}</div>
              )}
            </div>
          )}

          <div className="insights">
            <div className="insight">
              <div className="insight-label">Status</div>
              <div className="insight-value">
                {status === STATUS.loading
                  ? 'Analyzing'
                  : status === STATUS.success
                  ? 'Complete'
                  : status === STATUS.error
                  ? 'Failed'
                  : 'Idle'}
              </div>
            </div>
            <div className="insight">
              <div className="insight-label">Signal</div>
              <div className="insight-value">
                {result?.label === 1 ? 'High Risk' : result?.label === 0 ? 'Normal' : 'Pending'}
              </div>
            </div>
          </div>
        </section>
      </main>

      <input
        ref={galleryInputRef}
        type="file"
        accept="image/*"
        className="hidden-input"
        onChange={handlePickFile}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden-input"
        onChange={handlePickFile}
      />
    </div>
  );
}
