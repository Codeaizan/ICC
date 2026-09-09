import React from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import WhyAspects from '../components/WhyAspects';
import Methodology from '../components/Methodology';
import FinalCTA from '../components/FinalCTA';
import Footer from '../components/Footer';

export default function LandingPage() {
  return (
    <>
      <Navbar />
      <Hero />
      <WhyAspects />
      <Methodology />
      <FinalCTA />
      <Footer />
    </>
  );
}
