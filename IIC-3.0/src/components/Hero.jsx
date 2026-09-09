import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Zap } from 'lucide-react';
import './Hero.css';
import brainScan from '../assets/brain_scan.jpg';
import { generateId } from '../utils/storage';

export default function Hero() {
  const navigate = useNavigate();
  const [caseId, setCaseId] = useState('');
  const [modality, setModality] = useState('');
  const [sliceThickness, setSliceThickness] = useState('');
  const [isDemoLoaded, setIsDemoLoaded] = useState(false);

  const loadDemoScan = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/cases');
      if (response.ok) {
        const cases = await response.json();
        if (cases && cases.length > 0) {
          // Pick a random real case
          const randomCase = cases[Math.floor(Math.random() * cases.length)];
          const newCaseId = randomCase.case_id;
          setCaseId(newCaseId);
          setModality('NCCT');
          setSliceThickness('5mm');
          setIsDemoLoaded(true);
          navigate(`/analyze/${newCaseId}`);
          return;
        }
      }
    } catch (e) {
      console.error("Failed to load real cases, falling back");
    }
    
    // Fallback if backend is down
    const fallbackCases = ['0538941', '0538799', '0226142', '0091449'];
    const fallbackId = fallbackCases[Math.floor(Math.random() * fallbackCases.length)];
    setCaseId(fallbackId);
    setModality('NCCT');
    setSliceThickness('5mm');
    setIsDemoLoaded(true);
    navigate(`/analyze/${fallbackId}`);
  };

  const handleFileUpload = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      loadDemoScan();
    }
  };

  const handleAnalyze = () => {
    if (caseId) {
      navigate(`/analyze/${caseId}`);
    }
  };

  return (
    <section className="hero container animate-fade-in" id="product">
      <div className="hero-content">
        <div className="hero-text-section">
          <div className="eyebrow text-accent">AI-POWERED POST STROKE ASSESSMENT</div>
          <h1 className="heading-lg hero-title">
            Precision Post Stroke Scoring,<br />Automated.
          </h1>
          <p className="hero-subtitle text-muted">
            Accelerate critical treatment decisions with explainable, ML-powered ASPECTS analysis.
          </p>
        </div>

        <div className="analysis-card glass-card">
          <div className="upload-dropzone">
            <UploadCloud className="upload-icon text-accent" size={40} />
            <h3 className="upload-title">Drag & drop your CT scan here</h3>
            <p className="upload-subtitle text-muted">Supports .dcm, .nii, or .zip (Max 500MB)</p>

            <div className="upload-divider">
              <span>OR</span>
            </div>

            <label className="btn-secondary btn-browse" style={{ cursor: 'pointer', display: 'inline-block', textAlign: 'center' }}>
              Browse Files
              <input type="file" style={{ display: 'none' }} onChange={handleFileUpload} accept=".dcm,.nii,.zip,image/*" />
            </label>
          </div>

          <div className="scan-info-section">
            <div className="input-group">
              <label>CASE ID</label>
              <input
                type="text"
                placeholder="e.g. STK-001"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
              />
            </div>

            <div className="info-row">
              <div className="input-group">
                <label>MODALITY</label>
                <input
                  type="text"
                  value={modality}
                  onChange={(e) => setModality(e.target.value)}
                  placeholder="-"
                />
              </div>
              <div className="input-group">
                <label>SLICE THICKNESS</label>
                <input
                  type="text"
                  value={sliceThickness}
                  onChange={(e) => setSliceThickness(e.target.value)}
                  placeholder="-"
                />
              </div>
            </div>
          </div>

          <button
            className={`btn-primary analyze-btn ${!caseId ? 'disabled' : ''}`}
            onClick={handleAnalyze}
            disabled={!caseId}
          >
            <Zap size={18} />
            Analyze Scan
          </button>

          <div className="demo-divider">
            <span>or</span>
          </div>

          <button className="btn-demo" onClick={loadDemoScan}>
            <Zap size={18} />
            Load Demo Scan
          </button>
        </div>
      </div>

      <div className="hero-visual-sticky-wrapper">
        <div className="hero-visual">
          <div className="square-plate">
            <img src={brainScan} alt="AI Brain CT Scan" className="brain-image-zoomed" />
          </div>
        </div>
      </div>
    </section>
  );
}
