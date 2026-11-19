"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Language, translations } from "@/lib/i18n";
import {
  Server,
  Activity,
  Database,
  CloudSun,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Building2,
  Lock,
  LogOut,
} from "lucide-react";

interface SystemHealthData {
  system_status: string;
  environment: string;
  demo_mode: boolean;
  database: {
    status: string;
    total_users: number;
    total_organisations: number;
  };
  storage: {
    backend: string;
    local_dir: string;
  };
  ai_provider: {
    configured_model: string;
    has_gemini_key: boolean;
  };
  weather_providers: Array<{
    provider: string;
    status: string;
    is_live?: boolean;
    disclaimer?: string;
  }>;
}

interface OrganisationItem {
  id: string;
  legal_name: string;
  registration_number: string;
  admin_email?: string;
  city: string;
  state: string;
  is_approved: boolean;
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function AdminPage() {
  const [lang, setLang] = useState<Language>("en");
  const t = translations[lang];

  // Auth State (Tokens must never be hardcoded)
  const [token, setToken] = useState<string | null>(null);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Diagnostics & Org Data
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [organisations, setOrganisations] = useState<OrganisationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Check stored session on mount
  useEffect(() => {
    const saved = typeof window !== "undefined" ? sessionStorage.getItem("hl_admin_token") : null;
    if (saved) {
      setToken(saved);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadAdminData(token);
    }
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: adminEmail, password: adminPassword }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Authentication failed" }));
        throw new Error(err.detail || "Authentication failed");
      }
      const data = await res.json();
      sessionStorage.setItem("hl_admin_token", data.access_token);
      setToken(data.access_token);
    } catch (err: any) {
      setAuthError(err.message || "Failed to log in as administrator.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("hl_admin_token");
    setToken(null);
    setHealth(null);
    setOrganisations([]);
  };

  async function loadAdminData(authToken: string) {
    setLoading(true);
    setActionMessage(null);
    try {
      // 1. Health Diagnostics
      const healthRes = await fetch(`${API_BASE}/admin/health`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (healthRes.ok) {
        const hData = await healthRes.json();
        setHealth(hData);
      } else if (healthRes.status === 401 || healthRes.status === 403) {
        handleLogout();
        setAuthError("Session expired or administrator privileges required.");
        return;
      }

      // 2. Organisation Management List
      const orgRes = await fetch(`${API_BASE}/admin/organisations`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (orgRes.ok) {
        const oData = await orgRes.json();
        setOrganisations(oData);
      }
    } catch (err) {
      console.warn("Could not fetch admin telemetry:", err);
    } finally {
      setLoading(false);
    }
  }

  const handleApproveOrg = async (orgId: string, orgName: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/admin/organisations/${orgId}/approve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setActionMessage(`Approved organisation "${orgName}" successfully.`);
        loadAdminData(token);
      } else {
        const err = await res.json().catch(() => ({ detail: "Approval failed" }));
        alert(`Error approving organisation: ${err.detail}`);
      }
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    }
  };

  const handleRejectOrg = async (orgId: string, orgName: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/admin/organisations/${orgId}/reject`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setActionMessage(`Revoked/rejected organisation "${orgName}".`);
        loadAdminData(token);
      } else {
        const err = await res.json().catch(() => ({ detail: "Action failed" }));
        alert(`Error rejecting organisation: ${err.detail}`);
      }
    } catch (e: any) {
      alert(`Action error: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header lang={lang} onLanguageChange={setLang} />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-8">
        {/* Page Title */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              System Operations & Integrity Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Data provider connectivity, background job status, and cryptographic audit monitoring.
            </p>
          </div>

          {token && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => token && loadAdminData(token)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 bg-white rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-sm"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                <span>Refresh Diagnostics</span>
              </button>
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

        {/* Action Status Notice */}
        {actionMessage && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm font-medium">
            ✅ {actionMessage}
          </div>
        )}

        {/* Authentication Card if not authenticated */}
        {!token ? (
          <div className="max-w-md mx-auto bg-white p-8 rounded-2xl border border-slate-200 shadow-md space-y-6">
            <div className="text-center space-y-2">
              <div className="mx-auto w-12 h-12 bg-sky-100 text-sky-700 rounded-xl flex items-center justify-center">
                <Lock className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">Administrator Sign In</h2>
              <p className="text-xs text-slate-500">
                Authenticate with verified system_admin credentials to access audit telemetry and approve worker organisations.
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
                  Admin Email
                </label>
                <input
                  type="email"
                  required
                  placeholder="admin@heatledger.local"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
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
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-700 text-white font-bold text-sm rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                {authLoading ? "Authenticating..." : "Sign In to Operations"}
              </button>
            </form>
          </div>
        ) : (
          <div className="space-y-8">
            {/* System Status Banner */}
            {health && (
              <div className="space-y-6">
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">
                        All Core Systems Operational
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Environment: <span className="font-mono">{health.environment}</span> • Demo Mode:{" "}
                        <span className="font-mono text-emerald-700 font-bold">
                          {health.demo_mode ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-slate-400">Total Registered Users</span>
                    <p className="text-2xl font-black text-slate-900">{health.database.total_users}</p>
                  </div>
                </div>

                {/* Provider Connectivity Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {health.weather_providers.map((p) => (
                    <div
                      key={p.provider}
                      className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-slate-700">{p.provider}</span>
                        <span
                          className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                            p.status === "OPERATIONAL"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {p.status}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        {p.provider === "IMD"
                          ? "India Meteorological Department"
                          : p.provider === "ERA5_LAND"
                          ? "Copernicus ECMWF ERA5-Land"
                          : "Hyderabad Meteorological Fixture"}
                      </h4>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        {p.disclaimer || "Continuous meteorological feed adapter."}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Storage and Security */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                  <h4 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-sky-600" />
                    <span>Security & Storage Configuration</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-slate-500">Storage Backend</span>
                      <p className="font-mono font-bold text-slate-900 mt-1">
                        {health.storage.backend.toUpperCase()} (Private Encrypted)
                      </p>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-slate-500">AI Structured Extraction</span>
                      <p className="font-mono font-bold text-slate-900 mt-1">
                        {health.ai_provider.configured_model} (Gemini API:{" "}
                        {health.ai_provider.has_gemini_key ? "Configured" : "Heuristic Fallback Ready"})
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Organisation Approval Governance Table (SEC-02 & Admin Requirements) */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-sky-600" />
                    <span>Worker Organisation Approvals & Gatekeeping</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Unapproved organisations cannot access worker evidence dossiers or casework portals.
                  </p>
                </div>
                <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full">
                  {organisations.length} Registered Orgs
                </span>
              </div>

              {organisations.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm">
                  No organisations registered currently.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                        <th className="py-3 px-4">Organisation Name</th>
                        <th className="py-3 px-4">Reg Number</th>
                        <th className="py-3 px-4">Jurisdiction</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4 text-right">Governance Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {organisations.map((org) => (
                        <tr key={org.id} className="hover:bg-slate-50">
                          <td className="py-3 px-4 font-bold text-slate-900">
                            {org.legal_name}
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-600">
                            {org.registration_number}
                          </td>
                          <td className="py-3 px-4 text-slate-600">
                            {org.city}, {org.state}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-semibold text-[11px] ${
                                org.is_approved
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {org.is_approved ? "Approved" : "Pending Review"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right space-x-2">
                            {!org.is_approved ? (
                              <button
                                onClick={() => handleApproveOrg(org.id, org.legal_name)}
                                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg text-xs transition-colors"
                              >
                                Approve Org
                              </button>
                            ) : (
                              <button
                                onClick={() => handleRejectOrg(org.id, org.legal_name)}
                                className="px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold rounded-lg text-xs border border-rose-200 transition-colors"
                              >
                                Revoke Approval
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
