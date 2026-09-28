'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  FileText,
  GitCommit,
  Sparkles,
  Lock,
  Layers,
  Search,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Hash,
} from 'lucide-react';
import { governanceApi } from '@/lib/api';
import { AppShell } from '@/components/AppShell';
import {
  ApprovalRequestModel,
  GovernanceRecommendationModel,
  ChangeAuthorizationModel,
  GovernanceAuditRecordModel,
  EvidencePackageModel,
  CanApplyResultModel,
} from '@/types';

export default function GovernancePage() {
  const [activeTab, setActiveTab] = useState<'pending' | 'recommendations' | 'authorizations' | 'audit'>('pending');
  const [loading, setLoading] = useState(false);
  const [approvalRequests, setApprovalRequests] = useState<ApprovalRequestModel[]>([]);
  const [recommendations, setRecommendations] = useState<GovernanceRecommendationModel[]>([]);
  const [authorizations, setAuthorizations] = useState<ChangeAuthorizationModel[]>([]);
  const [auditRecords, setAuditRecords] = useState<GovernanceAuditRecordModel[]>([]);

  // Selected Request for Detail View
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequestModel | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<{
    decision?: any;
    authorization?: any;
    evidence_package?: EvidencePackageModel | null;
  } | null>(null);

  // Form states for Decision
  const [decisionMakerId, setDecisionMakerId] = useState('eng_lead@enterprise.org');
  const [decisionReason, setDecisionReason] = useState('');
  const [evidenceAck, setEvidenceAck] = useState(false);
  const [versionAck, setVersionAck] = useState(false);
  const [commitAck, setCommitAck] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // CanApply Gate Testing State (Slice 8A)
  const [selectedAuthForGate, setSelectedAuthForGate] = useState<ChangeAuthorizationModel | null>(null);
  const [gateTargetVersion, setGateTargetVersion] = useState<string>('');
  const [gateTargetCommit, setGateTargetCommit] = useState<string>('');
  const [gateEvidencePkgId, setGateEvidencePkgId] = useState<string>('');
  const [canApplyEvaluating, setCanApplyEvaluating] = useState<boolean>(false);
  const [canApplyResult, setCanApplyResult] = useState<CanApplyResultModel | null>(null);
  const [consumeLoading, setConsumeLoading] = useState<boolean>(false);

  const fetchData = async () => {
    setLoading(true);
    setActionError(null);
    try {
      const [reqs, recs, audits, auths] = await Promise.all([
        governanceApi.getApprovalRequests(),
        governanceApi.getRecommendations(),
        governanceApi.getAudit(),
        governanceApi.getAuthorizations().catch(() => []),
      ]);
      setApprovalRequests(reqs || []);
      setRecommendations(recs || []);
      setAuditRecords(audits || []);
      setAuthorizations(auths || []);

      if (auths && auths.length > 0 && !selectedAuthForGate) {
        setSelectedAuthForGate(auths[0]);
        setGateTargetVersion(auths[0].authorized_version || '1.0.0');
        setGateTargetCommit(auths[0].authorized_commit_sha || '');
        setGateEvidencePkgId(auths[0].evidence_package_id || '');
      }

      if (reqs && reqs.length > 0 && !selectedRequest) {
        handleSelectRequest(reqs[0]);
      }
    } catch (err: any) {
      console.error('Failed to load governance data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSelectRequest = async (req: ApprovalRequestModel) => {
    setSelectedRequest(req);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await governanceApi.getApprovalRequest(req.approval_request_id);
      setSelectedDetail({
        decision: res.decision,
        authorization: res.authorization,
        evidence_package: res.evidence_package,
      });
      setEvidenceAck(false);
      setVersionAck(false);
      setCommitAck(false);
      setDecisionReason('');
    } catch (err: any) {
      console.error('Failed to fetch request detail:', err);
    }
  };

  const handleApprove = async () => {
    if (!selectedRequest) return;
    setActionError(null);
    setActionSuccess(null);

    if (!evidenceAck || !versionAck) {
      setActionError('You must explicitly acknowledge the evidence package and target version.');
      return;
    }
    if (selectedRequest.proposed_commit_sha && !commitAck) {
      setActionError('You must explicitly acknowledge the target Git commit SHA.');
      return;
    }
    if (!decisionReason.trim()) {
      setActionError('Please provide a decision justification.');
      return;
    }

    try {
      await governanceApi.approveChange(
        selectedRequest.approval_request_id,
        {
          decision_reason: decisionReason,
          evidence_acknowledged: evidenceAck,
          version_acknowledged: versionAck,
          commit_acknowledged: commitAck,
          authorization_scope: 'PROMOTE',
        },
        decisionMakerId
      );
      setActionSuccess(`Change successfully authorized by ${decisionMakerId}! ChangeAuthorization issued.`);
      fetchData();
      if (selectedRequest) {
        handleSelectRequest(selectedRequest);
      }
    } catch (err: any) {
      setActionError(err.message || 'Failed to approve change.');
    }
  };

  const handleReject = async () => {
    if (!selectedRequest) return;
    setActionError(null);
    setActionSuccess(null);

    if (!decisionReason.trim()) {
      setActionError('Please provide a rejection justification.');
      return;
    }

    try {
      await governanceApi.rejectChange(
        selectedRequest.approval_request_id,
        { decision_reason: decisionReason },
        decisionMakerId
      );
      setActionSuccess(`Change rejected by ${decisionMakerId}. Status set to REJECTED.`);
      fetchData();
      if (selectedRequest) {
        handleSelectRequest(selectedRequest);
      }
    } catch (err: any) {
      setActionError(err.message || 'Failed to reject change.');
    }
  };

  const handleEvaluateCanApply = async () => {
    if (!selectedAuthForGate) return;
    setCanApplyEvaluating(true);
    setCanApplyResult(null);
    try {
      const res = await governanceApi.canApply(selectedAuthForGate.authorization_id, {
        change_type: selectedAuthForGate.authorized_change_type,
        subject_id: selectedAuthForGate.authorized_subject,
        target_version: gateTargetVersion || undefined,
        target_commit_sha: gateTargetCommit || undefined,
        current_evidence_package_id: gateEvidencePkgId || undefined,
        requested_scope: selectedAuthForGate.authorization_scope || 'PROMOTE',
      });
      setCanApplyResult(res);
    } catch (err: any) {
      setActionError(err.message || 'can_apply evaluation call failed.');
    } finally {
      setCanApplyEvaluating(false);
    }
  };

  const handleConsumeAuthorization = async (authId: string) => {
    setConsumeLoading(true);
    try {
      await governanceApi.consumeAuthorization(authId, decisionMakerId);
      setActionSuccess(`Authorization ${authId} successfully consumed (marked USED).`);
      fetchData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to consume authorization.');
    } finally {
      setConsumeLoading(false);
    }
  };

  const pendingCount = approvalRequests.filter((r) => r.status === 'PENDING').length;
  const approvedCount = approvalRequests.filter((r) => r.status === 'APPROVED').length;
  const rejectedCount = approvalRequests.filter((r) => r.status === 'REJECTED').length;

  return (
    <AppShell>
      <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-600 to-orange-500 p-[1px] shadow-[0_0_20px_rgba(245,158,11,0.3)]">
                <div className="h-full w-full bg-[#090d16] rounded-[11px] flex items-center justify-center">
                  <UserCheck className="h-5 w-5 text-amber-400" />
                </div>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white font-sans">
                Human Governance & Change Authorization Layer
              </h1>
            </div>
            <p className="text-sm text-slate-400">
              Deterministic gate enforcing human decision provenance, artifact-bound authorization, and tamper-evident evidence.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs uppercase tracking-wider font-semibold px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Authority Boundary
            </span>
            <span className="text-xs uppercase tracking-wider font-semibold px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Zero Autonomous Promotion
            </span>
            <button
              onClick={fetchData}
              className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/60 text-slate-300 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Core Operating Principle Alert */}
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 text-amber-200 text-xs sm:text-sm flex items-start space-x-3">
          <ShieldAlert className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <span className="font-semibold text-amber-300">Consequential Boundary Rule:</span>
            <p className="text-slate-300">
              AI can observe, test, evaluate, diagnose, and propose. <strong>Humans authorize consequential change.</strong>{' '}
              Approvals are immutable, time-bounded, and cryptographically tied to the exact artifact version and verified evidence hash.
            </p>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">Pending Human Decisions</div>
            <div className="text-2xl font-bold text-amber-400 mt-1">{pendingCount}</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">Authorized Changes</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{approvedCount}</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">Blocked / Rejected</div>
            <div className="text-2xl font-bold text-rose-400 mt-1">{rejectedCount}</div>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">AI Recommendations</div>
            <div className="text-2xl font-bold text-cyan-400 mt-1">{recommendations.length}</div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-2 border-b border-slate-800">
          <button
            onClick={() => setActiveTab('pending')}
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center space-x-2 ${
              activeTab === 'pending'
                ? 'border-amber-400 text-amber-300 bg-slate-900/80'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <UserCheck className="h-4 w-4" />
            <span>Pending Decisions ({pendingCount})</span>
          </button>
          <button
            onClick={() => setActiveTab('recommendations')}
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center space-x-2 ${
              activeTab === 'recommendations'
                ? 'border-cyan-400 text-cyan-300 bg-slate-900/80'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="h-4 w-4" />
            <span>AI Recommendations</span>
          </button>
          <button
            onClick={() => setActiveTab('authorizations')}
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center space-x-2 ${
              activeTab === 'authorizations'
                ? 'border-emerald-400 text-emerald-300 bg-slate-900/80'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="h-4 w-4" />
            <span>Authorizations & Gate ({authorizations.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center space-x-2 ${
              activeTab === 'audit'
                ? 'border-indigo-400 text-indigo-300 bg-slate-900/80'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="h-4 w-4" />
            <span>Immutable Audit Trail</span>
          </button>
        </div>

        {/* TAB 1: PENDING DECISIONS & DETAIL INSPECTOR */}
        {activeTab === 'pending' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left list: Requests */}
            <div className="lg:col-span-5 space-y-3">
              <h2 className="text-xs uppercase tracking-wider font-semibold text-slate-400">
                Change Approval Requests ({approvalRequests.length})
              </h2>

              {approvalRequests.length === 0 ? (
                <div className="p-8 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs">
                  No approval requests recorded.
                </div>
              ) : (
                approvalRequests.map((req) => {
                  const isSelected = selectedRequest?.approval_request_id === req.approval_request_id;
                  return (
                    <div
                      key={req.approval_request_id}
                      onClick={() => handleSelectRequest(req)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-800/80 border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.15)]'
                          : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs text-amber-400 font-semibold">
                          {req.approval_request_id}
                        </span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                            req.status === 'APPROVED'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : req.status === 'REJECTED'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {req.status}
                        </span>
                      </div>

                      <div className="text-sm font-semibold text-white mb-1">
                        {req.change_type}: {req.subject_id}
                      </div>

                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mt-2">
                        {req.proposed_version && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">
                            v{req.proposed_version}
                          </span>
                        )}
                        {req.proposed_commit_sha && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">
                            SHA: {req.proposed_commit_sha.slice(0, 7)}
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            req.risk_level === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-300'
                              : req.risk_level === 'HIGH'
                              ? 'bg-orange-500/20 text-orange-300'
                              : 'bg-blue-500/20 text-blue-300'
                          }`}
                        >
                          Risk: {req.risk_level}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Right: Approval Detail & Decision Action */}
            <div className="lg:col-span-7 space-y-4">
              {selectedRequest ? (
                <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-6">
                  {/* Top Banner */}
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <div className="text-xs text-slate-400">Target Consequential Change</div>
                      <div className="text-lg font-bold text-white mt-0.5">
                        {selectedRequest.change_type} on {selectedRequest.subject_id}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-slate-400">Effective Risk Gate</div>
                      <div className="text-sm font-bold text-amber-400 uppercase">
                        {selectedRequest.risk_level}
                      </div>
                    </div>
                  </div>

                  {/* Context Cards */}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-slate-400 block mb-1">Target Version</span>
                      <span className="font-mono text-cyan-300 font-semibold">
                        {selectedRequest.proposed_version || 'N/A'}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-slate-400 block mb-1">Target Git Commit</span>
                      <span className="font-mono text-cyan-300 font-semibold">
                        {selectedRequest.proposed_commit_sha || 'N/A'}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-slate-400 block mb-1">Evaluation Snapshot</span>
                      <span className="font-mono text-indigo-300">
                        {selectedRequest.evaluation_snapshot_id || 'N/A'}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-slate-400 block mb-1">Evidence Package ID</span>
                      <span className="font-mono text-indigo-300">
                        {selectedRequest.evidence_package_id}
                      </span>
                    </div>
                  </div>

                  {/* Verified Evidence Details */}
                  {selectedDetail?.evidence_package && (
                    <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          <span>Cryptographic Evidence Bundle</span>
                        </span>
                        <span className="font-mono text-[10px] text-slate-400">
                          SHA: {selectedDetail.evidence_package.content_hash.slice(0, 16)}...
                        </span>
                      </div>

                      {selectedDetail.evidence_package.observations.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-[11px] font-medium text-slate-400">Observations:</div>
                          <ul className="list-disc list-inside text-xs text-slate-300 space-y-0.5">
                            {selectedDetail.evidence_package.observations.map((obs, i) => (
                              <li key={i}>{obs}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {selectedDetail.evidence_package.regressions.length > 0 && (
                        <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                          <strong>Active Regressions Detected:</strong> {selectedDetail.evidence_package.regressions.join(', ')}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Existing Decision / Authorization Status */}
                  {selectedDetail?.decision && (
                    <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Recorded Decision:</span>
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded ${
                            selectedDetail.decision.decision === 'APPROVE'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-rose-500/20 text-rose-400'
                          }`}
                        >
                          {selectedDetail.decision.decision}
                        </span>
                      </div>
                      <div className="text-xs text-slate-300">
                        <strong>Decision Maker:</strong> {selectedDetail.decision.decision_maker_id} (
                        {selectedDetail.decision.actor_type})
                      </div>
                      <div className="text-xs text-slate-400">
                        <strong>Reason:</strong> {selectedDetail.decision.decision_reason}
                      </div>
                      {selectedDetail?.authorization && (
                        <div className="pt-2 border-t border-slate-700/60 text-xs font-mono text-amber-300">
                          Active Authorization: {selectedDetail.authorization.authorization_id} (
                          {selectedDetail.authorization.status})
                        </div>
                      )}
                    </div>
                  )}

                  {/* Decision Form (Only if PENDING) */}
                  {selectedRequest.status === 'PENDING' && (
                    <div className="pt-4 border-t border-slate-800 space-y-4">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400">
                        Human Authority Decision Action
                      </h3>

                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">
                          Authenticated Decision Maker Identity
                        </label>
                        <input
                          type="text"
                          value={decisionMakerId}
                          onChange={(e) => setDecisionMakerId(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500 font-mono"
                          placeholder="user@enterprise.org"
                        />
                        <span className="text-[10px] text-slate-500 block mt-1">
                          * AI agent identities (e.g. agent-*, ai-*) are rejected deterministically.
                        </span>
                      </div>

                      {/* Mandatory Acknowledgments */}
                      <div className="space-y-2 pt-1">
                        <label className="flex items-start space-x-2 text-xs text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={evidenceAck}
                            onChange={(e) => setEvidenceAck(e.target.checked)}
                            className="mt-0.5 rounded border-slate-700 bg-slate-950 text-amber-500 focus:ring-0"
                          />
                          <span>
                            I confirm that I have reviewed the verified evidence package and diagnostic reports for{' '}
                            <strong>{selectedRequest.subject_id}</strong>.
                          </span>
                        </label>

                        <label className="flex items-start space-x-2 text-xs text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={versionAck}
                            onChange={(e) => setVersionAck(e.target.checked)}
                            className="mt-0.5 rounded border-slate-700 bg-slate-950 text-amber-500 focus:ring-0"
                          />
                          <span>
                            I acknowledge that this approval is strictly bound to{' '}
                            <strong>v{selectedRequest.proposed_version || 'N/A'}</strong> and cannot authorize any other version.
                          </span>
                        </label>

                        {selectedRequest.proposed_commit_sha && (
                          <label className="flex items-start space-x-2 text-xs text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={commitAck}
                              onChange={(e) => setCommitAck(e.target.checked)}
                              className="mt-0.5 rounded border-slate-700 bg-slate-950 text-amber-500 focus:ring-0"
                            />
                            <span>
                              I acknowledge that this approval is strictly bound to Git commit{' '}
                              <strong>{selectedRequest.proposed_commit_sha}</strong>.
                            </span>
                          </label>
                        )}
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">
                          Decision Justification / Reason
                        </label>
                        <textarea
                          rows={2}
                          value={decisionReason}
                          onChange={(e) => setDecisionReason(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                          placeholder="Describe the engineering justification for this approval or rejection..."
                        />
                      </div>

                      {actionError && (
                        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                          {actionError}
                        </div>
                      )}
                      {actionSuccess && (
                        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs">
                          {actionSuccess}
                        </div>
                      )}

                      <div className="flex items-center space-x-3 pt-2">
                        <button
                          onClick={handleApprove}
                          className="flex-1 py-2 px-4 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-xs shadow-md transition-all"
                        >
                          Approve & Issue Change Authorization
                        </button>
                        <button
                          onClick={handleReject}
                          className="py-2 px-4 rounded-lg bg-slate-800 hover:bg-rose-950/40 text-rose-400 border border-rose-500/30 font-semibold text-xs transition-colors"
                        >
                          Reject Change
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs">
                  Select an approval request to inspect evidence and record decision.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: AI RECOMMENDATIONS */}
        {activeTab === 'recommendations' && (
          <div className="space-y-4">
            <h2 className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              System Recommendations (Advisory Only)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recommendations.map((rec) => (
                <div
                  key={rec.recommendation_id}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-cyan-400 font-semibold">
                      {rec.recommendation_id}
                    </span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {rec.source_system}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{rec.proposed_action}</h3>
                    <p className="text-xs text-slate-400 mt-1">{rec.rationale}</p>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-800/80 pt-2">
                    <span>Epistemic: {rec.epistemic_status}</span>
                    <span>Effective Risk: {rec.effective_risk || rec.risk_level}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: IMMUTABLE AUDIT TRAIL */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            <h2 className="text-xs uppercase tracking-wider font-semibold text-slate-400">
              Immutable Governance Audit Log
            </h2>
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono">
                  <tr>
                    <th className="p-3">Event ID</th>
                    <th className="p-3">Event Type</th>
                    <th className="p-3">Actor</th>
                    <th className="p-3">Subject</th>
                    <th className="p-3">SHA-256 Content Hash</th>
                    <th className="p-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300 font-mono text-[11px]">
                  {auditRecords.map((r) => (
                    <tr key={r.event_id} className="hover:bg-slate-800/40">
                      <td className="p-3 text-cyan-400">{r.event_id}</td>
                      <td className="p-3 font-semibold text-white">{r.event_type}</td>
                      <td className="p-3">
                        {r.actor_id}{' '}
                        <span className="text-[9px] text-slate-400">({r.actor_type})</span>
                      </td>
                      <td className="p-3">{r.subject_id}</td>
                      <td className="p-3 text-slate-400">{r.content_hash.slice(0, 16)}...</td>
                      <td className="p-3 text-slate-400">{r.timestamp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: AUTHORIZATIONS & CAN_APPLY GATE TESTER */}
        {activeTab === 'authorizations' && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2">
              <div>
                <h2 className="text-xs uppercase tracking-wider font-semibold text-slate-400 font-mono">
                  Issued Change Authorizations ({authorizations.length})
                </h2>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Cryptographically bound to target version, Git commit SHA, and verified evidence package hash.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: List of Authorizations */}
              <div className="lg:col-span-5 space-y-3">
                {authorizations.length === 0 ? (
                  <div className="p-8 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 font-mono text-xs">
                    No active change authorizations issued yet. Approve a pending change to issue an authorization.
                  </div>
                ) : (
                  authorizations.map((auth) => {
                    const isSelected = selectedAuthForGate?.authorization_id === auth.authorization_id;
                    return (
                      <div
                        key={auth.authorization_id}
                        onClick={() => {
                          setSelectedAuthForGate(auth);
                          setGateTargetVersion(auth.authorized_version || '');
                          setGateTargetCommit(auth.authorized_commit_sha || '');
                          setGateEvidencePkgId(auth.evidence_package_id || '');
                          setCanApplyResult(null);
                        }}
                        className={`p-4 rounded-xl border cursor-pointer transition-all font-mono text-xs ${
                          isSelected
                            ? 'bg-slate-900 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                            : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-bold text-emerald-400">{auth.authorization_id}</span>
                          <span
                            className={`text-[9px] uppercase px-2 py-0.5 rounded font-bold ${
                              auth.status === 'ACTIVE'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                : auth.status === 'USED'
                                ? 'bg-slate-800 text-slate-400'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                            }`}
                          >
                            {auth.status}
                          </span>
                        </div>
                        <div className="text-white font-semibold">{auth.authorized_subject}</div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          Scope: {auth.authorization_scope} · Version: v{auth.authorized_version || '1.0.0'}
                        </div>
                        <div className="text-[10px] text-slate-500 break-all mt-1">
                          SHA: {auth.evidence_package_hash.slice(0, 24)}...
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Right Column: Interactive Gate Tester */}
              <div className="lg:col-span-7">
                {selectedAuthForGate ? (
                  <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 space-y-6 font-mono">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-emerald-400">
                          Deterministic Enforcement Gate
                        </span>
                        <h3 className="text-base font-bold text-white mt-0.5">
                          can_apply() Gate Evaluation
                        </h3>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 block">STATUS</span>
                        <span className="text-xs font-bold text-white">{selectedAuthForGate.status}</span>
                      </div>
                    </div>

                    {/* Target Inputs for Gate Evaluation */}
                    <div className="space-y-4 text-xs">
                      <div>
                        <label className="block text-slate-400 text-[11px] mb-1 font-semibold">
                          Target Version (Must match authorized v{selectedAuthForGate.authorized_version || 'N/A'})
                        </label>
                        <input
                          type="text"
                          value={gateTargetVersion}
                          onChange={(e) => setGateTargetVersion(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                          placeholder="e.g. 1.0.0 or 1.1.0-unauthorized"
                        />
                      </div>

                      <div>
                        <label className="block text-slate-400 text-[11px] mb-1 font-semibold">
                          Target Git Commit SHA (Must match if bound)
                        </label>
                        <input
                          type="text"
                          value={gateTargetCommit}
                          onChange={(e) => setGateTargetCommit(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                          placeholder="e.g. a81f92d or wrong_sha"
                        />
                      </div>

                      <div>
                        <label className="block text-slate-400 text-[11px] mb-1 font-semibold">
                          Evidence Package ID
                        </label>
                        <input
                          type="text"
                          value={gateEvidencePkgId}
                          onChange={(e) => setGateEvidencePkgId(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                          placeholder="e.g. pkg_sample_01"
                        />
                      </div>

                      <div className="flex gap-3 pt-2">
                        <button
                          onClick={handleEvaluateCanApply}
                          disabled={canApplyEvaluating}
                          className="flex-1 py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center space-x-2"
                        >
                          <ShieldCheck className="h-4 w-4" />
                          <span>{canApplyEvaluating ? 'Evaluating Gate...' : 'Evaluate can_apply() Gate'}</span>
                        </button>

                        {selectedAuthForGate.status === 'ACTIVE' && (
                          <button
                            onClick={() => handleConsumeAuthorization(selectedAuthForGate.authorization_id)}
                            disabled={consumeLoading}
                            className="py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-slate-700 transition-colors"
                          >
                            {consumeLoading ? 'Consuming...' : 'Consume (Apply Change)'}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Gate Evaluation Result Banner */}
                    {canApplyResult && (
                      <div
                        className={`p-4 rounded-xl border space-y-2 ${
                          canApplyResult.decision === 'AUTHORIZED'
                            ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-200'
                            : 'bg-rose-950/20 border-rose-500/40 text-rose-200'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-sm flex items-center space-x-2">
                            {canApplyResult.decision === 'AUTHORIZED' ? (
                              <>
                                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                                <span>DECISION: AUTHORIZED (ALLOW)</span>
                              </>
                            ) : (
                              <>
                                <XCircle className="h-5 w-5 text-rose-400" />
                                <span>DECISION: BLOCKED (DENY)</span>
                              </>
                            )}
                          </span>
                          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-black/40">
                            Deterministic Enforcement
                          </span>
                        </div>

                        {canApplyResult.blockers && canApplyResult.blockers.length > 0 && (
                          <div className="pt-2 border-t border-rose-500/20 space-y-1">
                            <span className="text-[11px] font-bold text-rose-300">Enforcement Blockers:</span>
                            {canApplyResult.blockers.map((b, idx) => (
                              <div key={idx} className="text-xs text-rose-200 font-mono">
                                • {b}
                              </div>
                            ))}
                          </div>
                        )}

                        {canApplyResult.reasons && canApplyResult.reasons.length > 0 && (
                          <div className="pt-1 text-xs text-slate-300">
                            {canApplyResult.reasons.join(', ')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs font-mono">
                    Select a change authorization to evaluate can_apply() or test artifact mismatch.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

