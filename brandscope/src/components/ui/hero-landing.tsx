"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HeroLanding() {
  const router = useRouter();
  const [mouseGradientStyle, setMouseGradientStyle] = useState({ left: "0px", top: "0px", opacity: 0 });
  const [ripples, setRipples] = useState<{ id: number; x: number; y: number }[]>([]);

  useEffect(() => {
    const wordElements = document.querySelectorAll(".word-animate");
    const timeoutId = setTimeout(() => {
      wordElements.forEach((word) => {
        const delay = parseInt(word.getAttribute("data-delay") || "0");
        setTimeout(() => {
          if (word) (word as HTMLElement).style.animation = "word-appear 0.8s ease-out forwards";
        }, delay);
      });
    }, 300);
    return () => clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMouseGradientStyle({ left: `${e.clientX}px`, top: `${e.clientY}px`, opacity: 1 });
    };
    const handleMouseLeave = () => {
      setMouseGradientStyle((prev) => ({ ...prev, opacity: 0 }));
    };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const newRipple = { id: Date.now(), x: e.clientX, y: e.clientY };
      setRipples((prev) => [...prev, newRipple]);
      setTimeout(() => setRipples((prev) => prev.filter((r) => r.id !== newRipple.id)), 1000);
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const pageStyles = `
    #mouse-gradient-hero { position:fixed; pointer-events:none; border-radius:9999px; background-image:radial-gradient(circle, rgba(83,74,183,0.08), rgba(55,138,221,0.05), transparent 70%); transform:translate(-50%,-50%); will-change:left,top,opacity; transition:left 70ms linear,top 70ms linear,opacity 300ms ease-out; }
    @keyframes word-appear { 0%{opacity:0;transform:translateY(30px) scale(0.8);filter:blur(10px)} 50%{opacity:0.8;transform:translateY(10px) scale(0.95);filter:blur(2px)} 100%{opacity:1;transform:translateY(0) scale(1);filter:blur(0)} }
    @keyframes grid-draw { 0%{stroke-dashoffset:1000;opacity:0} 50%{opacity:0.3} 100%{stroke-dashoffset:0;opacity:0.15} }
    @keyframes pulse-glow { 0%,100%{opacity:0.1;transform:scale(1)} 50%{opacity:0.3;transform:scale(1.1)} }
    @keyframes float-particle { 0%,100%{transform:translateY(0);opacity:0.2} 50%{transform:translateY(-20px);opacity:0.6} }
    .word-animate { display:inline-block; opacity:0; margin:0 0.12em; transition:color 0.3s ease,transform 0.3s ease,text-shadow 0.3s ease; cursor:default; }
    .word-animate:hover { color:#a78bfa; transform:translateY(-3px); text-shadow:0 0 30px rgba(167,139,250,0.4); }
    .grid-line-hero { stroke:#534AB7; stroke-width:0.5; opacity:0; stroke-dasharray:5 5; stroke-dashoffset:1000; animation:grid-draw 2s ease-out forwards; }
    .detail-dot-hero { fill:#534AB7; opacity:0; animation:pulse-glow 3s ease-in-out infinite; }
    .corner-el { position:absolute; width:40px; height:40px; border:1px solid rgba(83,74,183,0.15); opacity:0; animation:word-appear 1s ease-out forwards; }
    .hero-underline { position:relative; }
    .hero-underline::after { content:''; position:absolute; bottom:-6px; left:0; width:0; height:2px; background:linear-gradient(90deg,transparent,#534AB7,transparent); animation:underline-grow 2s ease-out forwards; animation-delay:2.5s; }
    @keyframes underline-grow { to{width:100%} }
    .float-dot { position:absolute; width:2px; height:2px; background:#534AB7; border-radius:50%; opacity:0; animation:float-particle 4s ease-in-out infinite; }
    .ripple-hero { position:fixed; width:6px; height:6px; background:rgba(83,74,183,0.5); border-radius:50%; transform:translate(-50%,-50%); pointer-events:none; animation:pulse-glow 1s ease-out forwards; z-index:9999; }
  `;

  return (
    <>
      <style>{pageStyles}</style>
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-black to-slate-900 text-slate-100 overflow-hidden relative flex flex-col">

        {/* Background Grid */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <defs>
            <pattern id="heroGrid" width="80" height="80" patternUnits="userSpaceOnUse">
              <path d="M 80 0 L 0 0 0 80" fill="none" stroke="rgba(83,74,183,0.06)" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#heroGrid)" />
          <line x1="0" y1="30%" x2="100%" y2="30%" className="grid-line-hero" style={{ animationDelay: "0.5s" }} />
          <line x1="0" y1="70%" x2="100%" y2="70%" className="grid-line-hero" style={{ animationDelay: "1s" }} />
          <line x1="25%" y1="0" x2="25%" y2="100%" className="grid-line-hero" style={{ animationDelay: "1.5s" }} />
          <line x1="75%" y1="0" x2="75%" y2="100%" className="grid-line-hero" style={{ animationDelay: "2s" }} />
          <circle cx="25%" cy="30%" r="2" className="detail-dot-hero" style={{ animationDelay: "3s" }} />
          <circle cx="75%" cy="30%" r="2" className="detail-dot-hero" style={{ animationDelay: "3.2s" }} />
          <circle cx="25%" cy="70%" r="2" className="detail-dot-hero" style={{ animationDelay: "3.4s" }} />
          <circle cx="75%" cy="70%" r="2" className="detail-dot-hero" style={{ animationDelay: "3.6s" }} />
          <circle cx="50%" cy="50%" r="1.5" className="detail-dot-hero" style={{ animationDelay: "4s" }} />
        </svg>

        {/* Corner Elements */}
        <div className="corner-el top-6 left-6 md:top-10 md:left-10" style={{ animationDelay: "4s" }}><div className="absolute top-0 left-0 w-2 h-2 bg-purple-400 opacity-30 rounded-full" /></div>
        <div className="corner-el top-6 right-6 md:top-10 md:right-10" style={{ animationDelay: "4.2s" }}><div className="absolute top-0 right-0 w-2 h-2 bg-purple-400 opacity-30 rounded-full" /></div>
        <div className="corner-el bottom-6 left-6 md:bottom-10 md:left-10" style={{ animationDelay: "4.4s" }}><div className="absolute bottom-0 left-0 w-2 h-2 bg-purple-400 opacity-30 rounded-full" /></div>
        <div className="corner-el bottom-6 right-6 md:bottom-10 md:right-10" style={{ animationDelay: "4.6s" }}><div className="absolute bottom-0 right-0 w-2 h-2 bg-purple-400 opacity-30 rounded-full" /></div>

        {/* Floating Dots */}
        <div className="float-dot" style={{ top: "20%", left: "12%", animationDelay: "0.5s" }} />
        <div className="float-dot" style={{ top: "65%", left: "88%", animationDelay: "1s" }} />
        <div className="float-dot" style={{ top: "35%", left: "8%", animationDelay: "1.5s" }} />
        <div className="float-dot" style={{ top: "80%", left: "92%", animationDelay: "2s" }} />
        <div className="float-dot" style={{ top: "45%", left: "95%", animationDelay: "2.5s" }} />
        <div className="float-dot" style={{ top: "15%", left: "85%", animationDelay: "3s" }} />

        {/* Main Content */}
        <div className="relative z-10 min-h-screen flex flex-col justify-between items-center px-6 py-12 md:px-16 md:py-20">

          {/* Top */}
          <div className="text-center">
            <h2 className="text-xs sm:text-sm font-mono font-light text-slate-400 uppercase tracking-[0.3em]">
              <span className="word-animate" data-delay="0">Brand</span>
              <span className="word-animate" data-delay="200">Intelligence</span>
              <span className="word-animate" data-delay="400">Platform</span>
            </h2>
            <div className="mt-4 w-16 h-px bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-30 mx-auto" />
          </div>

          {/* Center — Hero */}
          <div className="text-center max-w-4xl mx-auto relative">
            <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold leading-none tracking-tight text-white hero-underline">
              <span className="word-animate" data-delay="600">OVAL</span>
            </h1>
            <div className="mt-6 md:mt-8">
              <h2 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-light text-slate-300 leading-relaxed tracking-wide">
                <span className="word-animate" data-delay="1200">See</span>
                <span className="word-animate" data-delay="1400">what</span>
                <span className="word-animate" data-delay="1600">they</span>
                <span className="word-animate" data-delay="1800">say</span>
                <span className="word-animate" data-delay="2000">before</span>
                <span className="word-animate" data-delay="2200">it</span>
                <span className="word-animate" data-delay="2400">spreads.</span>
              </h2>
            </div>

            {/* CTA Button */}
            <div className="mt-10 md:mt-14 opacity-0" style={{ animation: "word-appear 1s ease-out forwards", animationDelay: "3s" }}>
              <button
                onClick={() => router.push("/command-center")}
                className="group relative px-8 py-3 text-sm font-medium text-white border border-purple-500/30 rounded-full hover:border-purple-400/60 transition-all duration-500 cursor-pointer overflow-hidden"
              >
                <span className="relative z-10">Enter Dashboard</span>
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600/10 to-blue-600/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              </button>
            </div>

            {/* Side Lines */}
            <div className="absolute -left-8 top-1/2 -translate-y-1/2 w-4 h-px bg-purple-400 opacity-0" style={{ animation: "word-appear 1s ease-out forwards", animationDelay: "3.2s" }} />
            <div className="absolute -right-8 top-1/2 -translate-y-1/2 w-4 h-px bg-purple-400 opacity-0" style={{ animation: "word-appear 1s ease-out forwards", animationDelay: "3.4s" }} />
          </div>

          {/* Bottom */}
          <div className="text-center">
            <div className="mb-4 w-16 h-px bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-30 mx-auto" />
            <h2 className="text-xs sm:text-sm font-mono font-light text-slate-400 uppercase tracking-[0.25em]">
              <span className="word-animate" data-delay="3000">5 Platforms</span>
              <span className="word-animate mx-2 text-purple-400/40" data-delay="3100">&middot;</span>
              <span className="word-animate" data-delay="3200">1,907 Mentions</span>
              <span className="word-animate mx-2 text-purple-400/40" data-delay="3300">&middot;</span>
              <span className="word-animate" data-delay="3400">RAG-Powered</span>
            </h2>
            <div className="mt-6 flex justify-center space-x-4 opacity-0" style={{ animation: "word-appear 1s ease-out forwards", animationDelay: "4s" }}>
              <div className="w-1 h-1 bg-purple-400 rounded-full opacity-40" />
              <div className="w-1 h-1 bg-purple-400 rounded-full opacity-60" />
              <div className="w-1 h-1 bg-purple-400 rounded-full opacity-40" />
            </div>
          </div>
        </div>

        {/* Mouse Gradient */}
        <div
          id="mouse-gradient-hero"
          className="w-60 h-60 blur-xl sm:w-80 sm:h-80 sm:blur-2xl md:w-96 md:h-96 md:blur-3xl"
          style={{ left: mouseGradientStyle.left, top: mouseGradientStyle.top, opacity: mouseGradientStyle.opacity }}
        />

        {/* Click Ripples */}
        {ripples.map((ripple) => (
          <div key={ripple.id} className="ripple-hero" style={{ left: `${ripple.x}px`, top: `${ripple.y}px` }} />
        ))}
      </div>
    </>
  );
}
