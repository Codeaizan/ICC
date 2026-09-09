import React from 'react';
import { Activity, ClipboardCheck, Lightbulb } from 'lucide-react';
import './WhyAspects.css';

export default function WhyAspects() {
  const cards = [
    {
      icon: <Activity className="text-accent" size={32} />,
      title: "Faster Diagnosis",
      text: "Reduce time spent manually reviewing brain CT scans and identifying ischemic changes."
    },
    {
      icon: <ClipboardCheck className="text-accent" size={32} />,
      title: "Objective Scoring",
      text: "Standardize ASPECTS scoring and reduce subjectivity in stroke assessment."
    },
    {
      icon: <Lightbulb className="text-accent" size={32} />,
      title: "Explainable Results",
      text: "See region-level findings and understand how the final ASPECTS score is derived."
    }
  ];

  return (
    <section className="container section">
      <div className="section-header">
        <h2 className="text-accent eyebrow">Why Ischemic?</h2>
        <h3 className="heading-md">Fast. Objective. Explainable.</h3>
      </div>
      
      <div className="cards-grid">
        {cards.map((card, index) => (
          <div className="why-card glass-card" key={index}>
            <div className="card-icon">{card.icon}</div>
            <h4 className="card-title">{card.title}</h4>
            <p className="card-text text-muted">{card.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
