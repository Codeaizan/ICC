import React from 'react';
import { Upload, Layers, Brain, CheckCircle } from 'lucide-react';
import './Methodology.css';

export default function Methodology() {
  const steps = [
    {
      num: 1,
      icon: <Upload className="step-icon" size={28} />,
      title: "Upload CT Scan",
      text: "Securely upload an anonymized brain CT scan."
    },
    {
      num: 2,
      icon: <Layers className="step-icon" size={28} />,
      title: "Preprocess",
      text: "Prepare the scan for consistent AI analysis."
    },
    {
      num: 3,
      icon: <Brain className="step-icon" size={28} />,
      title: "Detect & Score",
      text: "AI identifies ischemic changes across ASPECTS regions."
    },
    {
      num: 4,
      icon: <CheckCircle className="step-icon" size={28} />,
      title: "Explainable Result",
      text: "Generate the final ASPECTS score with region-level findings."
    }
  ];

  return (
    <section className="container section" id="methodology">
      <div className="section-header">
        <h2 className="text-accent eyebrow">Methodology</h2>
        <h3 className="heading-md">How Ischemic Works</h3>
      </div>
      
      <div className="timeline-container glass-card">
        {steps.map((step, index) => (
          <React.Fragment key={index}>
            <div className="timeline-step">
              <div className="step-number">Step {step.num}</div>
              <div className="step-icon-container">{step.icon}</div>
              <h4 className="step-title">{step.title}</h4>
              <p className="step-text text-muted">{step.text}</p>
            </div>
            {index < steps.length - 1 && (
              <div className="timeline-connector"></div>
            )}
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}
