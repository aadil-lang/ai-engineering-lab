'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldCheck,
  Activity,
  Play,
  Sparkles,
  UserCheck,
  Terminal,
  FileSearch,
  Compass,
  Scale,
  GitBranch,
  Layers,
  HelpCircle,
  Cpu,
  Server,
  Database,
  ExternalLink,
  ChevronRight,
  Menu,
  X,
  Stethoscope,
  FolderGit2,
  Monitor
} from 'lucide-react';
import { api } from '@/lib/api';

interface AppShellProps {
  children: React.ReactNode;
  onOpenLaunchModal?: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({ children, onOpenLaunchModal }) => {
  const pathname = usePathname();
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        await api.getHealth();
        if (isMounted) setIsHealthy(true);
      } catch (err) {
        if (isMounted) setIsHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 20000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    {
      group: 'WORKSPACE',
      items: [
        { href: '/', label: 'Dashboard', icon: Activity, exact: true },
        { href: '/live', label: 'Live Testing Console', icon: Monitor },
        { href: '/change-impact', label: 'Change Impact & Regression', icon: Layers },
        { href: '/diagnosis', label: 'Failure Diagnoses', icon: Stethoscope },
        { href: '/prompts', label: 'Prompt Reliability Lab', icon: Sparkles },
        { href: '/evidence', label: 'Evidence Explorer', icon: FileSearch },
        { href: '/governance', label: 'Governance & Gate', icon: UserCheck },
      ],
    },
    {
      group: 'ENGINEERING & RELIABILITY',
      items: [
        { href: '/provenance', label: 'Engineering Provenance', icon: FolderGit2 },
        { href: '/reliability', label: 'Predictive Reliability', icon: Cpu },
        { href: '/cold-start', label: 'Cold-Start Calibration', icon: Compass },
        { href: '/uncertainty', label: 'Decision Uncertainty', icon: Scale },
        { href: '/lifecycle', label: 'CI/CD Lifecycle', icon: GitBranch },
      ],
    },
    {
      group: 'SYSTEM & CONTROL PLANE',
      items: [
        { href: '/tools', label: 'MCP / Agent Tools', icon: Terminal },
        { href: '/architecture', label: 'Architecture & Invariants', icon: Layers },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Top Banner Shell Header */}
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#070b14]/95 backdrop-blur-md">
        <div className="w-full px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>

            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-cyan-400 p-[1px] shadow-[0_0_15px_rgba(99,102,241,0.3)]">
                <div className="h-full w-full bg-[#080d1a] rounded-[7px] flex items-center justify-center group-hover:bg-[#0f172a] transition-colors">
                  <ShieldCheck className="h-4 w-4 text-indigo-400 group-hover:text-cyan-300 transition-colors" />
                </div>
              </div>
              <div className="flex flex-col">
                <div className="flex items-center space-x-2">
                  <span className="font-bold tracking-tight text-white font-mono text-sm">
                    AI RELIABILITY LAB
                  </span>
                  <span className="text-[9px] uppercase tracking-wider font-mono font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hidden sm:inline-block">
                    CONTROL CENTER
                  </span>
                </div>
              </div>
            </Link>
          </div>

          {/* Center system invariant notice */}
          <div className="hidden xl:flex items-center space-x-2 px-3 py-1 rounded-md bg-slate-950 border border-slate-800/80 text-[11px] text-slate-400 font-mono">
            <span className="text-cyan-400">Core Principle:</span>
            <span>AI explores & diagnoses · Humans authorize consequential change</span>
          </div>

          {/* Right System Status & Quick Actions */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-[11px] text-slate-300 font-mono">
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
                {isHealthy === true ? 'SYSTEM READY' : isHealthy === false ? 'BACKEND OFFLINE' : 'CHECKING...'}
              </span>
            </div>

            {onOpenLaunchModal ? (
              <button
                onClick={onOpenLaunchModal}
                className="relative group overflow-hidden rounded-lg p-[1px] font-medium text-xs shadow-[0_0_20px_rgba(99,102,241,0.25)] transition-all active:scale-95"
              >
                <span className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-cyan-400 to-indigo-500 transition-all duration-500 group-hover:scale-105" />
                <span className="relative flex items-center space-x-1.5 px-3 py-1.5 rounded-[7px] bg-slate-950 font-semibold text-white transition-colors group-hover:bg-slate-900">
                  <Play className="h-3.5 w-3.5 text-cyan-400 fill-cyan-400" />
                  <span className="font-mono">Test My App</span>
                </span>
              </button>
            ) : (
              <Link
                href="/?launch=true"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs text-white shadow-md transition-all"
              >
                <Play className="h-3.5 w-3.5 fill-white" />
                <span className="font-mono">Test My App</span>
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main Body with Sidebar + Content */}
      <div className="flex-1 flex w-full">
        {/* Engineering Sidebar */}
        <aside
          className={`fixed inset-y-14 left-0 z-30 w-64 border-r border-slate-800/80 bg-[#080d18] flex flex-col justify-between transition-transform duration-200 lg:static lg:translate-x-0 ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="p-4 space-y-6 overflow-y-auto">
            {navItems.map((group) => (
              <div key={group.group} className="space-y-1.5">
                <div className="px-2.5 text-[10px] font-mono uppercase tracking-wider font-semibold text-slate-500">
                  {group.group}
                </div>
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const isActive = item.exact
                      ? pathname === item.href
                      : pathname.startsWith(item.href);
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileMenuOpen(false)}
                        className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                          isActive
                            ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.15)] font-semibold'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                        }`}
                      >
                        <div className="flex items-center space-x-2.5">
                          <Icon
                            className={`h-4 w-4 ${
                              isActive ? 'text-cyan-400' : 'text-slate-500'
                            }`}
                          />
                          <span>{item.label}</span>
                        </div>
                        {isActive && (
                          <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Sidebar Footer with Active Application Context */}
          <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/60 space-y-2 text-[11px] font-mono">
            <div className="text-slate-400 flex items-center justify-between">
              <span className="text-[10px] uppercase text-slate-500">Active Target</span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
              <div className="text-white font-semibold truncate">Question Generator</div>
              <div className="text-[10px] text-slate-500 truncate">real_question_generator_local</div>
            </div>
          </div>
        </aside>

        {/* Primary Page Canvas */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#070b14]">
          {children}
        </main>
      </div>

      {/* Global Engineering Footer Status Bar */}
      <footer className="border-t border-slate-800/80 bg-[#060912] px-4 py-2 text-[11px] font-mono text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1.5">
            <Server className="h-3 w-3 text-slate-500" />
            <span>Environment: <strong className="text-slate-300">Local Lab</strong></span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Database className="h-3 w-3 text-slate-500" />
            <span>Backend: <strong className="text-emerald-400">Connected (FastAPI v1)</strong></span>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-slate-500">
          <span>Governance: <strong className="text-amber-400">Deterministic Gate ACTIVE</strong></span>
          <span>Version: <strong className="text-slate-300">Slice 8A.1</strong></span>
        </div>
      </footer>
    </div>
  );
};
