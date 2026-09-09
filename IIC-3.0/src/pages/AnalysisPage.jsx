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
  const [hoveredRegion, setHoveredRegion] = useState(null);

  const getRegionDescription = (name) => {
    switch(name) {
      case 'M1': return "Anterior MCA cortex";
      case 'M2': return "MCA cortex lateral to insular ribbon";
      case 'M3': return "Posterior MCA cortex";
      case 'M4': return "Anterior MCA territory superior to M1";
      case 'M5': return "Lateral MCA territory superior to M2";
      case 'M6': return "Posterior MCA territory superior to M3";
      case 'Insula': return "Insular ribbon";
      case 'Lentiform Nucleus': return "Putamen and globus pallidus";
      case 'Internal Capsule': return "Posterior limb of internal capsule";
      case 'Caudate': return "Head of caudate nucleus";
      default: return "";
    }
  };

  // Fetch scan from backend
  useEffect(() => {
    let isMounted = true;
    
    const fetchScan = async () => {
      setIsAnalyzing(true);
      setCurrentStep(0);
      
      // Start fetching data in parallel
      const dataPromise = getScanById(caseId);
      
      // Simulate AI loading steps (Random total time between 2 to 5 seconds)
      const totalTime = Math.floor(Math.random() * (5000 - 2000 + 1)) + 2000;
      const stepTime = totalTime / STEPS.length;
      
      for (let i = 0; i < STEPS.length; i++) {
        if (!isMounted) return;
        setCurrentStep(i);
        await new Promise(resolve => setTimeout(resolve, stepTime));
      }
      
      if (!isMounted) return;
      setCurrentStep(STEPS.length);
      
      const data = await dataPromise;
      
      if (!isMounted) return;
      
      if (data) {
        setScanData(data);
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
                {activeOverlay !== 'ASPECTS Regions' ? (
                  <>
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
                    {/* Legend for real CT Scan */}
                    <div className="viewer-legend absolute-legend" style={{ background: 'rgba(0,0,0,0.7)', padding: '5px', borderRadius: '4px' }}>
                      <div className="legend-item"><span className="legend-ring abnormal" style={{borderColor: 'red'}}></span> ML Assisted (Red)</div>
                      <div className="legend-item"><span className="legend-ring abnormal" style={{borderColor: 'yellow'}}></span> Hybrid Both (Yellow)</div>
                      <div className="legend-item"><span className="legend-ring abnormal" style={{borderColor: 'cyan'}}></span> Rule-Based Only (Cyan)</div>
                    </div>
                  </>
                ) : (
                  <>
                    <svg className="regions-svg-overlay" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
                      <defs>
                        <radialGradient id="brainGrad" cx="50%" cy="50%" r="50%">
                          <stop offset="0%" stopColor="#2a2a2a" />
                          <stop offset="80%" stopColor="#1a1a1a" />
                          <stop offset="100%" stopColor="#050505" />
                        </radialGradient>
                      </defs>
                      <rect x="0" y="0" width="100" height="100" fill="#050505" />
                      <circle cx="50" cy="50" r="49.5" fill="url(#brainGrad)" />
                      <line x1="50" y1="0" x2="50" y2="100" stroke="#151515" strokeWidth="0.5" />
                      <ellipse cx="54" cy="48" rx="2" ry="4" fill="#0a0a0a" />
                      
                      <text x="2" y="4" fill="#333" fontSize="2.5" fontFamily="monospace">SL:42/80</text>
                      <text x="2" y="98" fill="#333" fontSize="2.5" fontFamily="monospace">W:80 L:40</text>
                      <text x="98" y="98" fill="#333" fontSize="2.5" fontFamily="monospace" textAnchor="end">512x512</text>

                      <g className="aspects-regions-group">
                        {regions.map((r, i) => {
                          const isAbnormal = r.status === 'abnormal';
                          const className = `svg-region ${isAbnormal ? 'is-abnormal' : ''}`;
                          
                          let pathD = "";
                          let labelPos = { x: 0, y: 0 };
                          let label = r.name;
                          
                          switch (r.name) {
                            case 'M4':
                              pathD = "M 48.3 1.0 A 49 49 0 0 0 8.4 24.0 L 21.2 32.0 A 34 34 0 0 1 48.8 16.0 Z";
                              labelPos = { x: 28, y: 16 };
                              break;
                            case 'M1':
                              pathD = "M 48.8 17.0 A 33 33 0 0 0 22.0 32.5 L 33.0 39.4 A 20 20 0 0 1 49.3 30.0 Z";
                              labelPos = { x: 36, y: 26 };
                              break;
                            case 'M5':
                              pathD = "M 6.7 27.0 A 49 49 0 0 0 6.7 73.0 L 20.0 66.0 A 34 34 0 0 1 20.0 34.0 Z";
                              labelPos = { x: 14, y: 50 };
                              break;
                            case 'M2':
                              pathD = "M 20.9 34.5 A 33 33 0 0 0 20.9 65.5 L 32.3 59.4 A 20 20 0 0 1 32.3 40.6 Z";
                              labelPos = { x: 26, y: 50 };
                              break;
                            case 'M3':
                              pathD = "M 22.0 67.5 A 33 33 0 0 0 48.8 83.0 L 49.3 70.0 A 20 20 0 0 1 33.0 60.6 Z";
                              labelPos = { x: 36, y: 74 };
                              break;
                            case 'M6':
                              pathD = "M 8.4 76.0 A 49 49 0 0 0 48.3 99.0 L 48.8 84.0 A 34 34 0 0 1 21.2 68.0 Z";
                              labelPos = { x: 28, y: 84 };
                              break;
                            case 'Insula':
                              pathD = "M 31 42 A 1.5 8 0 1 0 31 58 A 1.5 8 0 1 0 31 42 Z";
                              labelPos = { x: 31, y: 50 };
                              label = "I";
                              break;
                            case 'Lentiform Nucleus':
                              pathD = "M 36 43 A 2 7 0 1 0 36 57 A 2 7 0 1 0 36 43 Z";
                              labelPos = { x: 36, y: 50 };
                              label = "L";
                              break;
                            case 'Internal Capsule':
                              pathD = "M 41 44 A 1.5 6 0 1 0 41 56 A 1.5 6 0 1 0 41 44 Z";
                              labelPos = { x: 41, y: 50 };
                              label = "IC";
                              break;
                            case 'Caudate':
                              pathD = "M 46 41 A 1.5 5 0 1 0 46 51 A 1.5 5 0 1 0 46 41 Z";
                              labelPos = { x: 46, y: 46 };
                              label = "C";
                              break;
                            default:
                              break;
                          }
                          
                          return (
                            <g 
                              key={i} 
                              className={className}
                              onMouseEnter={() => setHoveredRegion(r)}
                              onMouseLeave={() => setHoveredRegion(null)}
                              style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                            >
                              <path d={pathD} className="region-path" />
                              <text x={labelPos.x} y={labelPos.y} className="region-svg-label">{label}</text>
                            </g>
                          );
                        })}
                      </g>
                    </svg>
                    
                    {/* Hover Tooltip */}
                    {hoveredRegion && (
                      <div className="region-tooltip animate-fade-in" style={{
                        position: 'absolute',
                        top: '15px',
                        left: '15px',
                        background: 'rgba(10, 15, 20, 0.95)',
                        border: `1px solid ${hoveredRegion.status === 'abnormal' ? 'rgba(255, 60, 60, 0.5)' : 'rgba(100, 255, 218, 0.3)'}`,
                        padding: '12px 15px',
                        borderRadius: '8px',
                        zIndex: 100,
                        pointerEvents: 'none',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                        maxWidth: '220px',
                        backdropFilter: 'blur(4px)'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                          <div style={{ 
                            width: '8px', height: '8px', borderRadius: '50%', 
                            background: hoveredRegion.status === 'abnormal' ? 'var(--color-danger)' : 'var(--color-mint)' 
                          }}></div>
                          <strong style={{ color: 'white', fontSize: '1.05rem', letterSpacing: '0.5px' }}>{hoveredRegion.name}</strong>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '10px', lineHeight: '1.4' }}>
                          {getRegionDescription(hoveredRegion.name)}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                          <span style={{ color: hoveredRegion.status === 'abnormal' ? 'var(--color-danger)' : 'var(--color-mint)', fontWeight: '500' }}>
                            {hoveredRegion.status === 'abnormal' ? 'Ischemic Change' : 'Normal Tissue'}
                          </span>
                          <span style={{ color: 'var(--color-text-muted)' }}>
                            Conf: <span style={{ color: 'white', fontWeight: 'bold' }}>{hoveredRegion.confidence}%</span>
                          </span>
                        </div>
                      </div>
                    )}
                    
                    {/* Legend for SVG */}
                    <div className="viewer-legend absolute-legend">
                      <div className="legend-item"><span className="legend-dot ischemic"></span> Ischemic change</div>
                      <div className="legend-item"><span className="legend-ring normal"></span> Normal region</div>
                      <div className="legend-item"><span className="legend-ring abnormal"></span> Abnormal region</div>
                    </div>
                  </>
                )}
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
                
                {['Original', 'ASPECTS Regions', 'Combined'].map(mode => (
                  <button 
                    key={mode}
                    className={`toggle-btn ${activeOverlay === mode ? 'active' : ''}`}
                    onClick={() => setActiveOverlay(mode)}
                  >
                    {mode === 'Original' && <Eye size={16} />}
                    {mode === 'ASPECTS Regions' && <Grid size={16} />}
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
