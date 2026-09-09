import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  CheckCircle2, Circle, Loader2, ArrowLeft, Clock, 
  Search, ZoomIn, RotateCcw, Maximize2, Layers, Eye, Zap, Grid
} from 'lucide-react';
import { saveScan, getScanById } from '../utils/storage';
import brainScanImg from '../assets/brain_scan.jpg';
import './AnalysisPage.css';

const STEPS = [
  'Loading CT volume',
  'Preprocessing scan',
  'Detecting ischemic change',
  'Mapping ASPECTS regions',
  'Calculating score'
];

export default function AnalysisPage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(true);
  const [sliceIndex, setSliceIndex] = useState(42);
  const [activeOverlay, setActiveOverlay] = useState('Combined');
  const [scanData, setScanData] = useState(null);

  // Fetch scan from backend
  useEffect(() => {
    let isMounted = true;
    
    const fetchScan = async () => {
      setIsAnalyzing(true);
      const data = await getScanById(caseId);
      
      if (!isMounted) return;
      
      if (data) {
        setScanData(data);
        setCurrentStep(STEPS.length); // Skip straight to end
      }
      setIsAnalyzing(false);
    };
    
    fetchScan();
    
    return () => {
      isMounted = false;
    };
  }, [caseId]);

  if (isAnalyzing || !scanData) {
    return (
      <div className="analysis-page">
        <div className="analysis-header">
          <div className="header-left">
            <button className="back-btn" onClick={() => navigate('/')}>
              <ArrowLeft size={20} />
            </button>
            <div className="case-title">{caseId || 'STK-001'} <span className="case-modality">NCCT Analysis</span></div>
          </div>
        </div>
        
        <div className="loading-container">
          <div className="loading-card glass-card">
            <h2 className="loading-title">Analyzing Scan</h2>
            <p className="loading-subtitle">Processing CT volume with AI model...</p>
            
            <div className="loading-steps">
              {STEPS.map((step, index) => {
                let status = 'pending';
                if (index < currentStep) status = 'completed';
                if (index === currentStep) status = 'active';
                
                return (
                  <div key={index} className={`loading-step ${status}`}>
                    <div className="step-icon">
                      {status === 'completed' && <CheckCircle2 size={20} />}
                      {status === 'active' && <Loader2 size={20} />}
                      {status === 'pending' && <Circle size={20} />}
                    </div>
                    <span>{step}</span>
                  </div>
                );
              })}
            </div>
            
            <div className="progress-bar-container">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { regions, abnormalCount, score } = scanData;
  const abnormalRegionNames = regions.filter(r => r.status === 'abnormal').map(r => r.name).join(', ');

  return (
    <div className="analysis-page animate-fade-in">
      <div className="analysis-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate(-1)}>
            <ArrowLeft size={20} />
          </button>
          <div className="case-title">{caseId || 'STK-001'} <span className="case-modality">NCCT Analysis</span></div>
        </div>
        <div className="header-right">
          <div className="analysis-time">
            <Clock size={16} /> Analysis time: 4.2s
          </div>
          <button className="btn-secondary" onClick={() => navigate(`/report/${caseId}`)}>
            Detailed Report
          </button>
        </div>
      </div>
      
      <div className="results-container">
        {/* Main Left Area */}
        <div className="viewer-section">
          {/* CT Viewer */}
          <div className="ct-viewer-card glass-card">
            <div className="viewer-header">
              <div className="viewer-title">
                CT VIEWER <span>| Slice {sliceIndex} / 80</span>
              </div>
              <div className="viewer-controls">
                <button><Search size={18} /></button>
                <span style={{ fontSize: '0.85rem' }}>100%</span>
                <button><ZoomIn size={18} /></button>
                <button><RotateCcw size={18} /></button>
                <button><Maximize2 size={18} /></button>
              </div>
            </div>
            
            <div className="ct-image-container">
              <div className="ct-mock-image" style={{ transform: `scale(${1 + (sliceIndex - 40) * 0.005})`, background: '#050505' }}>
                {/* Display Real Image from Backend with CSS cropping magic */}
                <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', overflow: 'hidden', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                  <img 
                    src={`http://localhost:8000/data/${caseId}/overlay.png`} 
                    alt="CT Scan Overlay" 
                    style={{ 
                      width: '200%', 
                      height: '200%', 
                      objectFit: 'cover',
                      transform: `translate(${activeOverlay === 'Original' ? '25%' : '-25%'}, ${sliceIndex < 40 ? '25%' : '-25%'})`,
                      transition: 'transform 0.3s ease-in-out'
                    }}
                  />
                </div>
                
                {/* Legend */}
                <div className="viewer-legend absolute-legend" style={{ background: 'rgba(0,0,0,0.7)', padding: '5px', borderRadius: '4px' }}>
                  <div className="legend-item"><span className="legend-ring abnormal" style={{borderColor: 'red'}}></span> ML Assisted (Red)</div>
                  <div className="legend-item"><span className="legend-ring abnormal" style={{borderColor: 'yellow'}}></span> Hybrid Both (Yellow)</div>
                  <div className="legend-item"><span className="legend-ring abnormal" style={{borderColor: 'cyan'}}></span> Rule-Based Only (Cyan)</div>
                </div>
              </div>
            </div>
            
            <div className="viewer-footer">
              <div className="slice-slider-container">
                <span className="slice-label">SLICE</span>
                <input 
                  type="range" 
                  min="1" 
                  max="80" 
                  value={sliceIndex} 
                  onChange={(e) => setSliceIndex(e.target.value)}
                  className="slice-slider"
                />
                <span className="slice-value">{sliceIndex} / 80</span>
              </div>
              
              <div className="overlay-toggles">
                <span className="overlay-label">OVERLAY</span>
                
                {['Original', 'Combined'].map(mode => (
                  <button 
                    key={mode}
                    className={`toggle-btn ${activeOverlay === mode ? 'active' : ''}`}
                    onClick={() => setActiveOverlay(mode)}
                  >
                    {mode === 'Original' && <Eye size={16} />}
                    {mode === 'Combined' && <Layers size={16} />}
                    {mode}
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          {/* Summary Panel */}
          <div className="summary-card glass-card">
            <div className="summary-header">
              <Zap size={18} /> AI ANALYSIS SUMMARY
            </div>
            <div className="summary-text">
              <strong>{abnormalCount}</strong> of <strong>10</strong> ASPECTS regions show detected ischemic change.
              <br /><br />
              Affected regions: <strong>{abnormalCount > 0 ? abnormalRegionNames : 'None'}</strong>.
            </div>
            <div className="summary-calculation">
              <div style={{ fontSize: '0.8rem', color: 'var(--color-mint-light)', marginBottom: '0.5rem' }}>Score Calculation</div>
              10 - {abnormalCount} = {score}
            </div>
            <div className="disclaimer">
              AI-assisted ASPECTS estimation. For research/demo purposes only. Clinical decisions remain with qualified clinicians.
            </div>
          </div>
        </div>
        
        {/* Right Sidebar Score Area */}
        <div className="score-sidebar">
          <div className="score-card glass-card">
            <h3 className="score-title">ASPECTS SCORE</h3>
            <div className="score-circle">
              {/* Dynamic cut based on score */}
              <div className="score-circle-cut" style={{ clipPath: `polygon(50% 50%, 100% 0, 100% ${100 - (score/10)*100}%, 50% 50%)` }}></div>
              <span className="score-value">{score}</span>
              <span className="score-max">/ 10</span>
            </div>
            <p className="score-subtitle"><strong>{abnormalCount}</strong> regions affected</p>
          </div>
          
          <div className="regions-card glass-card">
            <div className="regions-header">
              <div className="regions-title">ASPECTS REGIONS</div>
              <div className="regions-count">10 regions</div>
            </div>
            
            <div className="regions-list">
              {regions.map((region, idx) => (
                <div key={idx} className={`region-item ${region.status}`}>
                  <div className="region-item-top">
                    <div className="region-name">
                      <div className="region-dot"></div>
                      {region.name}
                    </div>
                    <div className={`region-status ${region.status}`}>
                      {region.status === 'normal' ? <CheckCircle2 size={14} /> : <Circle size={14} fill="currentColor" />}
                      {region.status === 'normal' ? 'Normal' : 'Abnormal'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div className="region-confidence-bar">
                      <div className="confidence-fill" style={{ width: `${region.confidence}%` }}></div>
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{region.confidence}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
