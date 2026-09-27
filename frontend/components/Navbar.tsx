'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  ShieldCheck, 
  Activity, 
  Layers, 
  Terminal, 
  Play, 
  Radio, 
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Compass,
  Scale,
  GitBranch
} from 'lucide-react';
import { api } from '@/lib/api';

interface NavbarProps {
  onOpenLaunchModal?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenLaunchModal }) => {
  const pathname = usePathname();
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.getHealth();
        setIsHealthy(true);
      } catch (err) {
        setIsHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border/80 bg-[#070b14]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 p-[1px] shadow-[0_0_15px_rgba(99,102,241,0.4)]">
              <div className="h-full w-full bg-[#090d16] rounded-[11px] flex items-center justify-center group-hover:bg-[#0f172a] transition-colors">
                <ShieldCheck className="h-5 w-5 text-indigo-400 group-hover:text-cyan-300 transition-colors" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold tracking-tight text-white font-sans text-sm sm:text-base">
                  Antigravity QA
                </span>
                <span className="text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Slice v1
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                AI Application Reliability & Predictive QA Platform
              </p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-800">
            <Link
              href="/"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Activity className="h-3.5 w-3.5" />
                <span>Test Runs</span>
              </div>
            </Link>

            <Link
              href="/reliability"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/reliability'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                <span>Reliability & Predictive QA</span>
              </div>
            </Link>

            <Link
              href="/cold-start"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/cold-start'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Compass className="h-3.5 w-3.5 text-purple-400" />
                <span>Cold-Start</span>
              </div>
            </Link>

            <Link
              href="/uncertainty"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/uncertainty'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Scale className="h-3.5 w-3.5 text-amber-400" />
                <span>Uncertainty & Decisions</span>
              </div>
            </Link>

            <Link
              href="/tools"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/tools'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                <span>Agent Tools</span>
              </div>
            </Link>

            <Link
              href="/lifecycle"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/lifecycle'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <GitBranch className="h-3.5 w-3.5 text-cyan-400" />
                <span>Lifecycle</span>
              </div>
            </Link>

            <Link
              href="/prompts"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname.startsWith('/prompts')
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Sparkles className="h-3.5 w-3.5 text-pink-400" />
                <span>Prompt Lab</span>
              </div>
            </Link>

            <Link
              href="/architecture"
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                pathname === '/architecture'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <Layers className="h-3.5 w-3.5" />
                <span>Architecture</span>
              </div>
            </Link>
          </nav>
        </div>

        {/* Right Action Bar */}
        <div className="flex items-center space-x-3">
          {/* Health Indicator */}
          <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy === true
                  ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse'
                  : isHealthy === false
                  ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]'
                  : 'bg-amber-400'
              }`}
            />
            <span className="hidden sm:inline">
              {isHealthy === true
                ? 'Local Engine Active'
                : isHealthy === false
                ? 'Backend Disconnected'
                : 'Checking Engine...'}
            </span>
          </div>

          {/* Quick Launch Button */}
          {onOpenLaunchModal && (
            <button
              onClick={onOpenLaunchModal}
              className="relative group overflow-hidden rounded-lg p-[1px] font-medium text-xs shadow-[0_0_20px_rgba(99,102,241,0.3)] transition-all active:scale-95"
            >
              <span className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-cyan-400 to-indigo-500 transition-all duration-500 group-hover:scale-105" />
              <span className="relative flex items-center space-x-2 px-3.5 py-1.5 rounded-[7px] bg-slate-950 font-semibold text-white transition-colors group-hover:bg-slate-900">
                <Play className="h-3.5 w-3.5 text-cyan-400 fill-cyan-400" />
                <span>Launch Test Run</span>
              </span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
