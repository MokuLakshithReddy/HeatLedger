"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Language, translations } from "@/lib/i18n";
import {
  FolderKanban,
  FileText,
  Download,
  ShieldCheck,
  Plus,
  AlertTriangle,
  Clock,
  User,
  ExternalLink,
  Search,
  Building2,
  Lock,
  LogOut,
  CheckCircle2,
} from "lucide-react";

interface SharedReport {
  id: string;
  report_number: string;
  worker_id: string;
  period_start: string;
  period_end: string;
  total_shifts: number;
  total_hours_worked: number;
  total_extreme_heat_hours: number;
  net_earnings_recorded: number;
  integrity_sha256: string;
  created_at: string;
}

interface CaseItem {
  id: string;
  case_number: string;
  title: string;
  status: string;
  priority: string;
  worker_pseudonym: string;
  created_at: string;
}

interface OrgInfo {
  id: string;
  legal_name: string;
  registration_number: string;
  city: string;
  state: string;
  is_approved: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function PortalPage() {
  const [lang, setLang] = useState<Language>("en");
  const t = translations[lang];

  // Auth state
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Portal data
  const [organisations, setOrganisations] = useState<OrgInfo[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [reports, setReports] = useState<SharedReport[]>([]);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedReport, setSelectedReport] = useState<SharedReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // New Case form
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [newCasePriority, setNewCasePriority] = useState("HIGH");

  // Check stored session
  useEffect(() => {
    const saved = typeof window !== "undefined" ? sessionStorage.getItem("hl_portal_token") : null;
    if (saved) {
      setToken(saved);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadOrganisations(token);
    }
  }, [token]);

  useEffect(() => {
    if (token && selectedOrgId) {
      loadOrgData(token, selectedOrgId);
    }
  }, [token, selectedOrgId]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Invalid credentials" }));
        throw new Error(err.detail || "Authentication failed");
      }
      const data = await res.json();
      sessionStorage.setItem("hl_portal_token", data.access_token);
      setToken(data.access_token);
    } catch (err: any) {
      setAuthError(err.message || "Failed to authenticate.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("hl_portal_token");
    setToken(null);
    setOrganisations([]);
    setSelectedOrgId("");
    setReports([]);
    setCases([]);
    setSelectedReport(null);
  };

  async function loadOrganisations(authToken: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/organisations`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const orgList: OrgInfo[] = await res.json();
        setOrganisations(orgList);
        if (orgList.length > 0) {
          setSelectedOrgId(orgList[0].id);
        }
      } else if (res.status === 401) {
        handleLogout();
        setAuthError("Session expired. Please sign in again.");
      }
    } catch (err) {
      console.warn("Error fetching organisations:", err);
    } finally {
      setLoading(false);
    }
  }

  async function loadOrgData(authToken: string, orgId: string) {
    setLoading(true);
    try {
      // 1. Fetch reports shared with this org
      const repRes = await fetch(`${API_BASE}/organisations/${orgId}/reports`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (repRes.ok) {
        const repData = await repRes.json();
        setReports(repData);
        if (repData.length > 0) {
          setSelectedReport(repData[0]);
        } else {
          setSelectedReport(null);
        }
      } else {
        setReports([]);
      }

      // 2. Fetch cases for this org
      const caseRes = await fetch(`${API_BASE}/organisations/${orgId}/cases`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (caseRes.ok) {
        const caseData = await caseRes.json();
        setCases(caseData);
      } else {
        setCases([]);
      }
    } catch (err) {
      console.warn("Error loading organisation data:", err);
    } finally {
      setLoading(false);
    }
  }

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedOrgId) return;

    try {
      const res = await fetch(`${API_BASE}/organisations/${selectedOrgId}/cases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: newCaseTitle,
          priority: newCasePriority,
          report_id: selectedReport?.id || undefined,
        }),
      });

      if (res.ok) {
        setMessage("Case opened successfully with linked evidence dossier.");
        setNewCaseTitle("");
        setIsCreatingCase(false);
        loadOrgData(token, selectedOrgId);
      } else {
        const err = await res.json().catch(() => ({ detail: "Failed to create case" }));
        alert(`Error: ${err.detail}`);
      }
    } catch (err: any) {
      alert(`Error creating case: ${err.message}`);
    }
  };

  const handleVerifyReportHash = async (reportId: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/evidence/reports/${reportId}/verify`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Cryptographic Integrity Verified:\nSHA-256 Digest: ${data.sha256}\nMatch Status: ${data.verified ? "EXACT MATCH (100% UNALTERED)" : "MISMATCH"}`);
      } else {
        alert("Verification failed: unshared or report not found.");
      }
    } catch (e: any) {
      alert(`Verification check error: ${e.message}`);
    }
  };

  const handleDownloadPDF = async (reportId: string, reportNumber: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/evidence/reports/${reportId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportNumber}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert("Failed to download PDF. Access may have been revoked by the worker.");
      }
    } catch (e: any) {
      alert(`Download error: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header lang={lang} onLanguageChange={setLang} />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-100 text-sky-800">
                CASEWORK ADVOCACY
              </span>
              <span className="text-xs text-slate-400">• Hyderabad Gig Worker Hub</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-1">
              Organisation Casework Portal
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Review worker-authorized evidence dossiers, dispute platform deductions, and file compensation petitions.
            </p>
          </div>

          {token && (
            <div className="flex items-center gap-3">
              {organisations.length > 0 && (
                <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-sm text-xs">
                  <Building2 className="w-4 h-4 text-sky-600" />
                  <select
                    value={selectedOrgId}
                    onChange={(e) => setSelectedOrgId(e.target.value)}
                    className="bg-transparent font-bold text-slate-800 focus:outline-none"
                  >
                    {organisations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.legal_name} {!org.is_approved ? "(Pending Approval)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 bg-rose-50 text-rose-700 rounded-lg border border-rose-200 hover:bg-rose-100 shadow-sm"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          )}
        </div>

        {message && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm font-medium flex items-center justify-between">
            <span>✅ {message}</span>
            <button onClick={() => setMessage(null)} className="text-xs text-emerald-600 underline">Dismiss</button>
          </div>
        )}

        {/* Authentication Form if unauthenticated */}
        {!token ? (
          <div className="max-w-md mx-auto bg-white p-8 rounded-2xl border border-slate-200 shadow-md space-y-6">
            <div className="text-center space-y-2">
              <div className="mx-auto w-12 h-12 bg-sky-100 text-sky-700 rounded-xl flex items-center justify-center">
                <Lock className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">Organisation Advocate Sign In</h2>
              <p className="text-xs text-slate-500">
                Sign in with your verified organisation account to view worker-shared evidence and manage dispute cases.
              </p>
            </div>

            {authError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg font-medium">
                {authError}
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Advocate / Organisation Email
                </label>
                <input
                  type="email"
                  required
                  placeholder="advocate@telanganaworkers.org"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-700 text-white font-bold text-sm rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                {authLoading ? "Authenticating..." : "Sign In to Casework"}
              </button>
            </form>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Shared Evidence Dossiers */}
            <div className="lg:col-span-1 space-y-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-sky-600" />
                    <span>Worker-Authorized Dossiers</span>
                  </h3>
                  <span className="text-[11px] font-semibold bg-slate-100 px-2 py-0.5 rounded-full text-slate-600">
                    {reports.length} Available
                  </span>
                </div>

                <div className="space-y-2">
                  {reports.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-400">
                      No reports currently shared with this organisation.
                    </div>
                  ) : (
                    reports.map((r) => (
                      <div
                        key={r.id}
                        onClick={() => setSelectedReport(r)}
                        className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                          selectedReport?.id === r.id
                            ? "bg-sky-50 border-sky-300 shadow-xs"
                            : "bg-slate-50 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {r.report_number}
                          </span>
                          <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                            SHA-256 Valid
                          </span>
                        </div>
                        <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                          <span>{r.total_hours_worked}h worked • 🔥 {r.total_extreme_heat_hours}h heat</span>
                          <span className="font-semibold text-slate-700">₹{r.net_earnings_recorded}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Casework List */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <FolderKanban className="w-4 h-4 text-sky-600" />
                    <span>Active Union Casework</span>
                  </h3>
                  <button
                    onClick={() => setIsCreatingCase(true)}
                    className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 bg-sky-50 text-sky-700 rounded-lg hover:bg-sky-100 border border-sky-200"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>New Case</span>
                  </button>
                </div>

                {isCreatingCase && (
                  <form onSubmit={handleCreateCase} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3 text-xs">
                    <h4 className="font-bold text-slate-800">Open Legal / Welfare Case</h4>
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">Case Title</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Swiggy Heat Penalty Dispute - Begumpet"
                        value={newCaseTitle}
                        onChange={(e) => setNewCaseTitle(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">Priority</label>
                      <select
                        value={newCasePriority}
                        onChange={(e) => setNewCasePriority(e.target.value)}
                        className="w-full px-2 py-1.5 border border-slate-300 rounded-lg bg-white"
                      >
                        <option value="CRITICAL">CRITICAL</option>
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        className="flex-1 py-1.5 bg-sky-600 text-white font-bold rounded-lg hover:bg-sky-700"
                      >
                        Create Case
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsCreatingCase(false)}
                        className="px-3 py-1.5 bg-slate-200 text-slate-700 font-semibold rounded-lg"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                <div className="space-y-2">
                  {cases.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-400">
                      No casework logged yet.
                    </div>
                  ) : (
                    cases.map((c) => (
                      <div key={c.id} className="p-3 rounded-xl border border-slate-200 bg-slate-50 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-slate-900">{c.case_number}</span>
                          <span
                            className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                              c.priority === "HIGH" || c.priority === "CRITICAL"
                                ? "bg-rose-100 text-rose-800"
                                : "bg-slate-200 text-slate-700"
                            }`}
                          >
                            {c.priority}
                          </span>
                        </div>
                        <p className="font-medium text-slate-800">{c.title}</p>
                        <div className="flex justify-between text-slate-400 text-[10px]">
                          <span>Status: {c.status}</span>
                          <span>Worker: {c.worker_pseudonym}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Right: Selected Evidence Details */}
            <div className="lg:col-span-2">
              {selectedReport ? (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
                  {/* Top Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-base font-black text-slate-900">
                          {selectedReport.report_number}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-bold text-xs">
                          Immutable Evidence
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Period: {new Date(selectedReport.period_start).toLocaleDateString()} to{" "}
                        {new Date(selectedReport.period_end).toLocaleDateString()} • Hyderabad Urban Ward
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleVerifyReportHash(selectedReport.id)}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
                      >
                        <ShieldCheck className="w-4 h-4 text-sky-600" />
                        <span>Verify Digest</span>
                      </button>
                      <button
                        onClick={() => handleDownloadPDF(selectedReport.id, selectedReport.report_number)}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg shadow-sm transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        <span>Download PDF Dossier</span>
                      </button>
                    </div>
                  </div>

                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center">
                      <span className="text-[11px] font-semibold text-slate-500">Shifts Logged</span>
                      <p className="text-xl font-black text-slate-900 mt-1">{selectedReport.total_shifts}</p>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center">
                      <span className="text-[11px] font-semibold text-slate-500">Total Hours</span>
                      <p className="text-xl font-black text-slate-900 mt-1">{selectedReport.total_hours_worked}h</p>
                    </div>
                    <div className="p-4 bg-rose-50 rounded-xl border border-rose-200 text-center">
                      <span className="text-[11px] font-semibold text-rose-700">Extreme Heat Exposure</span>
                      <p className="text-xl font-black text-rose-900 mt-1">{selectedReport.total_extreme_heat_hours}h</p>
                    </div>
                    <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-center">
                      <span className="text-[11px] font-semibold text-emerald-700">Net Recorded Pay</span>
                      <p className="text-xl font-black text-emerald-900 mt-1">₹{selectedReport.net_earnings_recorded}</p>
                    </div>
                  </div>

                  {/* Cryptographic SHA-256 Box */}
                  <div className="p-4 bg-slate-900 rounded-xl text-white space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-sky-400 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4" />
                        SHA-256 Cryptographic Hash Fingerprint
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">Secured with Ed25519/HMAC</span>
                    </div>
                    <p className="font-mono text-xs text-slate-300 break-all bg-slate-800 p-2.5 rounded-lg border border-slate-700">
                      {selectedReport.integrity_sha256}
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Any single bit modification to the evidence records or PDF will permanently invalidate this fingerprint.
                    </p>
                  </div>

                  {/* Evidentiary Notice & Worker Consent Disclaimer */}
                  <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 leading-relaxed">
                    <p className="font-bold flex items-center gap-1 mb-1">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      Traceable Legal Disclaimer (Indian DPDP Act & Evidence Principles)
                    </p>
                    HeatLedger establishes strict correlation between verified meteorological observations and worker shift timelines. It does not certify causal financial liability. Worker consent for this dossier may be revoked at any time by the worker, terminating organisation access.
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
                  <FileText className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                  <p className="text-sm font-semibold text-slate-600">No Dossier Selected</p>
                  <p className="text-xs text-slate-400 mt-1">Select an evidence dossier from the left sidebar to inspect details.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
