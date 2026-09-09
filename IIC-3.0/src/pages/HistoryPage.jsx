import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History as HistoryIcon, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { getHistory } from '../utils/storage';
import './HistoryPage.css';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory(getHistory());
  }, []);

  // Calculate stats
  const totalCases = history.length;
  const avgScore = totalCases > 0 
    ? (history.reduce((sum, item) => sum + item.score, 0) / totalCases).toFixed(1)
    : 0;
  const totalAbnormal = history.filter(item => item.abnormalCount > 0).length;

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className="history-page animate-fade-in">
      <div className="history-header">
        <div className="history-title-icon">
          <HistoryIcon size={28} />
        </div>
        <div>
          <h1>Analysis History</h1>
          <p>{totalCases} analyses completed</p>
        </div>
      </div>
      
      {totalCases > 0 ? (
        <>
          <div className="stats-container">
            <div className="stat-card glass-card">
              <span className="stat-value">{totalCases}</span>
              <span className="stat-label">TOTAL CASES</span>
            </div>
            <div className="stat-card glass-card">
              <span className="stat-value">{avgScore}</span>
              <span className="stat-label">AVG SCORE</span>
            </div>
            <div className="stat-card glass-card">
              <span className="stat-value">{totalAbnormal}</span>
              <span className="stat-label">ABNORMAL</span>
            </div>
          </div>
          
          <div className="history-list">
            {history.map((item, index) => (
              <div 
                key={index} 
                className="history-item"
                onClick={() => navigate(`/analyze/${item.id}`)}
              >
                <div className="item-score">{item.score}</div>
                <div className="item-details">
                  <div className="item-title">
                    {item.id} 
                    <span className="item-status">
                      {item.abnormalCount > 0 
                        ? <><AlertCircle size={14} style={{color: 'var(--color-accent)'}} /> {item.abnormalCount} affected</>
                        : <><CheckCircle2 size={14} style={{color: 'var(--color-accent)'}} /> Normal</>
                      }
                    </span>
                  </div>
                  <div className="item-date">
                    <Clock size={12} />
                    {formatDate(item.date)}
                  </div>
                </div>
                <div className="item-arrow">{item.score}/10 &gt;</div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="history-empty">
          <h2 className="empty-title">No scans analyzed yet.</h2>
          <p className="empty-subtitle">Upload a CT scan to begin your first analysis.</p>
          <button className="btn-primary" onClick={() => navigate('/')}>+ New Scan</button>
        </div>
      )}
      
      <div style={{ textAlign: 'center', marginTop: '3rem', fontSize: '0.75rem', color: 'rgba(167, 227, 212, 0.4)' }}>
        <AlertCircle size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }}/>
        AI-assisted ASPECTS estimation - For research/demo purposes only
      </div>
    </div>
  );
}
