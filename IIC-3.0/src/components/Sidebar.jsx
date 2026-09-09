import React from 'react';
import { NavLink } from 'react-router-dom';
import { PlusCircle, History, BrainCircuit } from 'lucide-react';
import './Sidebar.css';

export default function Sidebar() {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <div className="logo-container">
          <BrainCircuit className="logo-icon text-accent" size={28} />
          <div className="logo-text">
            <span className="logo-brand">Ischemic</span>
            <span className="logo-sub">RESEARCH PROTOTYPE</span>
          </div>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink to="/" className="nav-item">
          <PlusCircle size={20} />
          <span>New Scan</span>
        </NavLink>
        
        <NavLink to="/history" className="nav-item">
          <History size={20} />
          <span>History</span>
        </NavLink>
      </nav>
      
      <div className="sidebar-footer">
        <div className="system-status">
          <div className="status-indicator"></div>
          <span>System Ready</span>
        </div>
        <div className="version">v1.0.0 — Demo</div>
      </div>
    </aside>
  );
}
