import React from 'react';
import './FinalCTA.css';

export default function FinalCTA() {
  return (
    <section className="container section">
      <div className="cta-container glass-card text-center">
        <h2 className="heading-md cta-title">Ready to Analyze a Scan?</h2>
        <p className="cta-subtitle text-muted">
          Upload a CT scan and experience fast, objective, explainable stroke assessment.
        </p>
        <button className="btn-primary cta-btn">Analyze Scan</button>
      </div>
    </section>
  );
}
