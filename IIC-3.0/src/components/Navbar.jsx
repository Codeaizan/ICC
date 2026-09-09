import React from 'react';
import './Navbar.css';

export default function Navbar() {
  return (
    <nav className="navbar container">
      <div className="navbar-logo">
        <span className="logo-text">Ischemic</span>
      </div>
      <div className="navbar-links">
        <a href="#product">Product</a>
        <a href="#methodology">Methodology</a>
        <a href="#resources">Resources</a>
      </div>
    </nav>
  );
}
