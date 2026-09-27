import React from 'react';
import { Activity, CheckCircle2, Clock, Database, Layers } from 'lucide-react';
import { TestRun } from '@/types';
import { formatDuration } from '@/lib/utils';

interface MetricCardsProps {
  runs: TestRun[];
}

export const MetricCards: React.FC<MetricCardsProps> = ({ runs }) => {
  const totalRuns = runs.length;
  const passedRuns = runs.filter(r => r.status === 'PASSED').length;
  const failedRuns = runs.filter(r => r.status === 'FAILED' || r.status === 'ERROR').length;
  
  const passRate = totalRuns > 0 ? Math.round((passedRuns / totalRuns) * 100) : 100;
  
  const avgDuration = totalRuns > 0 
    ? Math.round(runs.reduce((acc, r) => acc + (r.duration_ms || 0), 0) / totalRuns) 
    : 0;

  const totalEvidenceCount = runs.reduce((acc, r) => acc + (r.evidence_ids?.length || 0), 0);

  const stats = [
    {
      title: 'Total Test Runs',
      value: totalRuns,
      subtext: `${passedRuns} passed · ${failedRuns} failed`,
      icon: Activity,
      accent: 'text-indigo-400',
      borderGlow: 'hover:border-indigo-500/40',
      bgGradient: 'from-indigo-500/10 to-transparent',
    },
    {
      title: 'Reliability Pass Rate',
      value: `${passRate}%`,
      subtext: passRate >= 90 ? 'Healthy target baseline' : 'Attention required',
      icon: CheckCircle2,
      accent: passRate >= 90 ? 'text-emerald-400' : 'text-amber-400',
      borderGlow: passRate >= 90 ? 'hover:border-emerald-500/40' : 'hover:border-amber-500/40',
      bgGradient: passRate >= 90 ? 'from-emerald-500/10 to-transparent' : 'from-amber-500/10 to-transparent',
    },
    {
      title: 'Avg Execution Latency',
      value: formatDuration(avgDuration),
      subtext: '5 simulated actions / run',
      icon: Clock,
      accent: 'text-cyan-400',
      borderGlow: 'hover:border-cyan-500/40',
      bgGradient: 'from-cyan-500/10 to-transparent',
    },
    {
      title: 'Evidence Records',
      value: totalEvidenceCount,
      subtext: 'DOM, Screenshots, HAR, Logs',
      icon: Database,
      accent: 'text-purple-400',
      borderGlow: 'hover:border-purple-500/40',
      bgGradient: 'from-purple-500/10 to-transparent',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, idx) => {
        const Icon = stat.icon;
        return (
          <div
            key={idx}
            className={`relative overflow-hidden rounded-xl border border-surface-border bg-gradient-to-b ${stat.bgGradient} bg-[#0e1626] p-5 shadow-lg backdrop-blur-sm transition-all duration-200 ${stat.borderGlow}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {stat.title}
              </span>
              <div className={`p-2 rounded-lg bg-slate-900/80 border border-slate-800 ${stat.accent}`}>
                <Icon className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold tracking-tight text-white font-mono">
                {stat.value}
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {stat.subtext}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
