'use client';

import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  ShieldCheck, 
  Play, 
  RefreshCw, 
  Sliders,
  Send,
  Eye,
  FileCode,
  Hash,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Database
} from 'lucide-react';
import { api } from '@/lib/api';
import { AppShell } from '@/components/AppShell';
import { ToolCapability, ToolDefinitionDetail, AuditEventRecord, ToolEnvelope } from '@/types';

export default function ToolsDeveloperPage() {
  const [capabilities, setCapabilities] = useState<ToolCapability[]>([]);
  const [selectedToolName, setSelectedToolName] = useState<string>('inspect_application');
  const [toolDetail, setToolDetail] = useState<ToolDefinitionDetail | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEventRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
  const [isInvoking, setIsInvoking] = useState<boolean>(false);
  const [invocationPayload, setInvocationPayload] = useState<string>('{\n  "application_id": "app_inventory"\n}');
  const [invocationResponse, setInvocationResponse] = useState<ToolEnvelope | null>(null);
  const [activeTab, setActiveTab] = useState<'schemas' | 'invoke' | 'audit'>('invoke');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load capabilities & audit log
  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [caps, audits] = await Promise.all([
        api.getToolCapabilities(),
        api.getRecentToolAudit(25),
      ]);
      setCapabilities(caps);
      setAuditEvents(audits);
      if (caps.length > 0 && !selectedToolName) {
        setSelectedToolName(caps[0].name);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load control plane data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Load tool detail when selected tool changes
  useEffect(() => {
    if (!selectedToolName) return;
    const fetchDetail = async () => {
      setIsDetailLoading(true);
      try {
        const detail = await api.getToolDefinition(selectedToolName);
        setToolDetail(detail);

        // Prepopulate sensible default payload for each tool
        if (selectedToolName === 'inspect_application' || selectedToolName === 'get_application_health' || selectedToolName === 'get_prediction' || selectedToolName === 'get_uncertainty' || selectedToolName === 'get_reliability_summary') {
          setInvocationPayload(JSON.stringify({ application_id: 'app_inventory' }, null, 2));
        } else if (selectedToolName === 'start_test_session') {
          setInvocationPayload(JSON.stringify({
            application_id: 'app_inventory',
            mode: 'reliability',
            scope: 'autonomous-verification',
            max_duration_seconds: 300,
            idempotency_key: `key_${Date.now()}`
          }, null, 2));
        } else if (selectedToolName === 'list_failures') {
          setInvocationPayload(JSON.stringify({ application_id: 'app_inventory', limit: 5 }, null, 2));
        } else if (selectedToolName === 'get_failure') {
          setInvocationPayload(JSON.stringify({ failure_id: 'fail_sample_01' }, null, 2));
        } else if (selectedToolName === 'diagnose_failure') {
          setInvocationPayload(JSON.stringify({ failure_id: 'fail_sample_01', depth: 'standard' }, null, 2));
        } else if (selectedToolName === 'get_evidence') {
          setInvocationPayload(JSON.stringify({ evidence_id: 'ev_sample_01' }, null, 2));
        }
      } catch (err: any) {
        console.error('Failed to load tool detail', err);
      } finally {
        setIsDetailLoading(false);
      }
    };
    fetchDetail();
  }, [selectedToolName]);

  const handleInvoke = async () => {
    if (!selectedToolName) return;
    setIsInvoking(true);
    setInvocationResponse(null);
    setErrorMsg(null);
    try {
      let parsedPayload: Record<string, any> = {};
      try {
        parsedPayload = JSON.parse(invocationPayload);
      } catch {
        throw new Error('Payload is not valid JSON');
      }

      const env = await api.invokeTool(selectedToolName, parsedPayload, {
        actor: 'developer_console',
        session_id: 'sess_dev_inspect',
      });
      setInvocationResponse(env);
      // Refresh audit logs
      const updatedAudits = await api.getRecentToolAudit(25);
      setAuditEvents(updatedAudits);
    } catch (err: any) {
      setErrorMsg(err.message || 'Tool execution failed');
    } finally {
      setIsInvoking(false);
    }
  };

  const selectedCap = capabilities.find(c => c.name === selectedToolName);

  return (
    <AppShell>
      <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Header Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-surface-border/80 gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 p-[1px] shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                <div className="h-full w-full bg-[#090d16] rounded-[11px] flex items-center justify-center">
                  <Terminal className="h-5 w-5 text-emerald-400" />
                </div>
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                    Reliability Control Plane & Agent Tools
                  </h1>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    MCP-Ready v1.0
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                  Canonical typed, audited, and redacted application-facing tool boundary for autonomous agents.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-surface-card border border-surface-border text-xs font-medium text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Control Plane</span>
            </button>
            <div className="px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-[11px] font-mono text-emerald-400 flex items-center space-x-1.5">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Redaction & Audit Active</span>
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs flex items-center space-x-3">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Main Grid: Tools List + Details Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Registered Tools (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-surface-card border border-surface-border rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-surface-border/60">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                  <Sliders className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Canonical Tool Registry ({capabilities.length})</span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Transport: Decoupled</span>
              </div>

              <div className="space-y-1.5">
                {capabilities.map((tool) => {
                  const isSelected = tool.name === selectedToolName;
                  const isAction = tool.mode === 'ACTION';

                  return (
                    <button
                      key={tool.name}
                      onClick={() => setSelectedToolName(tool.name)}
                      className={`w-full text-left p-3 rounded-lg border transition-all flex items-start justify-between group ${
                        isSelected
                          ? 'bg-indigo-950/40 border-indigo-500/50 shadow-[0_0_10px_rgba(99,102,241,0.15)]'
                          : 'bg-slate-900/40 border-surface-border/40 hover:bg-slate-800/40 hover:border-slate-700'
                      }`}
                    >
                      <div className="space-y-1 pr-2">
                        <div className="flex items-center space-x-2">
                          <span className={`font-mono text-xs font-bold ${isSelected ? 'text-indigo-300' : 'text-slate-200'}`}>
                            {tool.name}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 line-clamp-1">
                          {tool.description}
                        </p>
                      </div>

                      <div className="flex flex-col items-end space-y-1 shrink-0">
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${
                            isAction
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                          }`}
                        >
                          {tool.mode}
                        </span>
                        <span className="text-[9px] font-mono text-slate-400">
                          v{tool.version}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* MCP Server Live Status Panel */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-emerald-500/30 text-xs space-y-3 shadow-[0_0_15px_rgba(16,185,129,0.08)]">
              <div className="flex items-center justify-between border-b border-surface-border/60 pb-2">
                <span className="font-semibold text-white flex items-center space-x-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>MCP Server: RUNNING</span>
                </span>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
                  v7.3.0
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                <div>
                  <span className="text-slate-400 block text-[9px] uppercase">Protocol</span>
                  <span className="text-slate-200">2024-11-05</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[9px] uppercase">SDK Version</span>
                  <span className="text-slate-200">mcp 2.2.0</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[9px] uppercase">Contract</span>
                  <span className="text-slate-200">reliability-tools/v1</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[9px] uppercase">Tools Count</span>
                  <span className="text-emerald-300 font-bold">10 canonical</span>
                </div>
              </div>

              <div className="space-y-1 pt-1 border-t border-surface-border/40 text-[11px]">
                <span className="text-slate-400 block text-[10px] font-semibold uppercase">Active Transports:</span>
                <div className="flex items-center space-x-2 text-emerald-400 font-mono">
                  <CheckCircle2 className="h-3 w-3 shrink-0" />
                  <span>STDIO (scripts/run_mcp_server.py)</span>
                </div>
                <div className="flex items-center space-x-2 text-emerald-400 font-mono">
                  <CheckCircle2 className="h-3 w-3 shrink-0" />
                  <span>Streamable HTTP (/mcp)</span>
                </div>
                <div className="text-[10px] text-slate-400 pt-0.5 font-mono truncate">
                  Endpoint: http://127.0.0.1:8000/mcp
                </div>
              </div>

              {/* Last MCP Invocation Telemetry */}
              {auditEvents.length > 0 && (
                <div className="p-2.5 rounded-lg bg-[#070b14] border border-surface-border/60 space-y-1 text-[10px] font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="font-semibold text-slate-300">Last Tool Invocation:</span>
                    <span className="text-emerald-400 font-bold">{auditEvents[0].result_status}</span>
                  </div>
                  <div className="text-slate-200 truncate">
                    Tool: <span className="text-cyan-300">{auditEvents[0].tool_name}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Latency: {auditEvents[0].execution_time_ms ? `${auditEvents[0].execution_time_ms.toFixed(1)}ms` : '-'}</span>
                    <span>Actor: {auditEvents[0].actor}</span>
                  </div>
                  <div className="text-slate-400 truncate">
                    Req ID: {auditEvents[0].request_id}
                  </div>
                </div>
              )}
            </div>

            {/* Transport Decoupling Summary */}
            <div className="p-4 rounded-xl bg-slate-900/40 border border-surface-border/60 text-xs space-y-2">
              <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
                <Database className="h-3.5 w-3.5 text-indigo-400" />
                <span>MCP Adapter Boundary</span>
              </span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                The Model Context Protocol acts as an external transport adapter over the canonical Reliability Tool Registry. Domain logic, predictive intelligence, and evaluation evidence remain completely independent.
              </p>
            </div>
          </div>

          {/* Right Column: Active Tool Workbench (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            <div className="bg-surface-card border border-surface-border rounded-xl shadow-sm overflow-hidden">
              {/* Tool Header */}
              <div className="p-5 border-b border-surface-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/30">
                <div>
                  <div className="flex items-center space-x-3">
                    <h2 className="text-lg font-bold font-mono text-white">
                      {selectedToolName}
                    </h2>
                    {selectedCap && (
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                          selectedCap.mode === 'ACTION'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                        }`}
                      >
                        {selectedCap.mode}
                      </span>
                    )}
                    <span className="text-xs font-mono text-slate-400">
                      version {toolDetail?.version || '1.0'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {toolDetail?.description || selectedCap?.description}
                  </p>
                </div>

                {/* Tabs */}
                <div className="flex items-center space-x-1 bg-slate-950/60 p-1 rounded-lg border border-surface-border/60 self-start sm:self-auto">
                  <button
                    onClick={() => setActiveTab('invoke')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                      activeTab === 'invoke'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Invocation Studio
                  </button>
                  <button
                    onClick={() => setActiveTab('schemas')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                      activeTab === 'schemas'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Contract Schemas
                  </button>
                  <button
                    onClick={() => setActiveTab('audit')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                      activeTab === 'audit'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Audit Trail ({auditEvents.length})
                  </button>
                </div>
              </div>

              {/* Tab 1: Invocation Studio */}
              {activeTab === 'invoke' && (
                <div className="p-5 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Request Editor */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                          <Send className="h-3 w-3 text-cyan-400" />
                          <span>Request JSON</span>
                        </label>
                        <span className="text-[10px] text-slate-400">application_id: app_inventory / app_booking / app_eda</span>
                      </div>
                      <textarea
                        value={invocationPayload}
                        onChange={(e) => setInvocationPayload(e.target.value)}
                        rows={10}
                        className="w-full bg-[#090d16] border border-surface-border rounded-lg p-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500 transition-colors"
                      />
                      <button
                        onClick={handleInvoke}
                        disabled={isInvoking}
                        className="w-full py-2 px-4 rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-medium text-xs shadow-md shadow-indigo-950 flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
                      >
                        {isInvoking ? (
                          <>
                            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                            <span>Invoking Control Plane...</span>
                          </>
                        ) : (
                          <>
                            <Play className="h-3.5 w-3.5 fill-current" />
                            <span>Execute Tool ({selectedToolName})</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Response Viewer */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                          <Eye className="h-3 w-3 text-emerald-400" />
                          <span>Audited Response Envelope</span>
                        </label>
                        {invocationResponse && (
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                            invocationResponse.success
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          }`}>
                            {invocationResponse.success ? 'SUCCESS (200)' : 'FAILED'}
                          </span>
                        )}
                      </div>

                      <div className="relative">
                        <pre className="w-full h-[270px] bg-[#090d16] border border-surface-border rounded-lg p-3 text-xs font-mono text-emerald-300 overflow-auto">
                          {invocationResponse
                            ? JSON.stringify(invocationResponse, null, 2)
                            : '// Response payload will appear here after execution...\n// Includes: success, data, error, metadata, and cryptographic provenance.'}
                        </pre>
                      </div>

                      {invocationResponse && (
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
                          <span>Latency: {invocationResponse.metadata?.execution_time_ms?.toFixed(2)}ms</span>
                          <span>Snapshot: {invocationResponse.metadata?.provenance?.snapshot_id || 'eval_snap_slice_7_1'}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Contract Schemas */}
              {activeTab === 'schemas' && (
                <div className="p-5 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Input Schema */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                          <FileCode className="h-3 w-3 text-cyan-400" />
                          <span>Input Schema (Pydantic / JSON Schema)</span>
                        </span>
                      </div>
                      <pre className="w-full h-[320px] bg-[#090d16] border border-surface-border rounded-lg p-3 text-xs font-mono text-cyan-200 overflow-auto">
                        {toolDetail?.input_schema
                          ? JSON.stringify(toolDetail.input_schema, null, 2)
                          : '// Loading schema...'}
                      </pre>
                    </div>

                    {/* Output Schema */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                          <FileCode className="h-3 w-3 text-emerald-400" />
                          <span>Output Schema (Pydantic / JSON Schema)</span>
                        </span>
                      </div>
                      <pre className="w-full h-[320px] bg-[#090d16] border border-surface-border rounded-lg p-3 text-xs font-mono text-emerald-200 overflow-auto">
                        {toolDetail?.output_schema
                          ? JSON.stringify(toolDetail.output_schema, null, 2)
                          : '// Loading schema...'}
                      </pre>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Audit Trail */}
              {activeTab === 'audit' && (
                <div className="p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                      <Hash className="h-3 w-3 text-amber-400" />
                      <span>Cryptographic Control Plane Audit Log</span>
                    </span>
                    <span className="text-[11px] text-slate-400">Zero raw secrets logged; SHA-256 digests</span>
                  </div>

                  <div className="overflow-x-auto border border-surface-border rounded-lg bg-[#090d16]">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/60 border-b border-surface-border text-slate-400 font-mono text-[11px]">
                        <tr>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Tool</th>
                          <th className="py-2.5 px-3">App ID</th>
                          <th className="py-2.5 px-3">Actor</th>
                          <th className="py-2.5 px-3">Request SHA-256</th>
                          <th className="py-2.5 px-3">Latency</th>
                          <th className="py-2.5 px-3">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border/40 font-mono text-[11px]">
                        {auditEvents.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="py-6 text-center text-slate-400">
                              No recent audit events recorded.
                            </td>
                          </tr>
                        ) : (
                          auditEvents.map((evt) => (
                            <tr key={evt.event_id} className="hover:bg-slate-800/30 transition-colors">
                              <td className="py-2 px-3">
                                {evt.result_status === 'SUCCESS' ? (
                                  <span className="text-emerald-400 flex items-center space-x-1">
                                    <CheckCircle2 className="h-3 w-3" />
                                    <span>OK</span>
                                  </span>
                                ) : (
                                  <span className="text-rose-400 flex items-center space-x-1">
                                    <XCircle className="h-3 w-3" />
                                    <span>{evt.error_code || 'ERR'}</span>
                                  </span>
                                )}
                              </td>
                              <td className="py-2 px-3 font-semibold text-slate-200">
                                {evt.tool_name}
                              </td>
                              <td className="py-2 px-3 text-slate-400">
                                {evt.application_id || '-'}
                              </td>
                              <td className="py-2 px-3 text-cyan-400">
                                {evt.actor}
                              </td>
                              <td className="py-2 px-3 text-slate-400" title={evt.request_sha256}>
                                {evt.request_sha256 ? `${evt.request_sha256.slice(0, 12)}...` : '-'}
                              </td>
                              <td className="py-2 px-3 text-slate-300">
                                {evt.execution_time_ms ? `${evt.execution_time_ms.toFixed(1)}ms` : '-'}
                              </td>
                              <td className="py-2 px-3 text-slate-400">
                                {new Date(evt.timestamp).toLocaleTimeString()}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
