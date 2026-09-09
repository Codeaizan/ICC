import React from 'react';
import './Footer.css';

export default function Footer() {
  return (
    <footer className="footer container">
      <div className="footer-content">
        <div className="footer-logo">Ischemic</div>
        <div className="footer-links">
          <a href="#">Privacy Policy</a>
          <a href="#">Terms of Service</a>
          <a href="#">Contact</a>
        </div>
      </div>
      <div className="footer-bottom">
        <p className="text-muted">&copy; {new Date().getFullYear()} Ischemic. All rights reserved. For research purposes only.</p>
      </div>
    </footer>
  );
}
