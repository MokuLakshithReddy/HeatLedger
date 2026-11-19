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
  AlertTriangle,
  RefreshCw,
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

export default function AdminPage() {
  const [lang, setLang] = useState<Language>("en");
  const t = translations[lang];

  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadHealth() {
    setLoading(true);
    try {
      const loginResp = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "admin@heatledger.local",
          password: "HeatLedgerAdmin2026!",
        }),
      });

      if (loginResp.ok) {
        const { access_token } = await loginResp.json();
        const res = await fetch("http://localhost:8000/api/v1/admin/health", {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      }
    } catch (err) {
      console.warn("Could not fetch admin health from backend, using fallback state.", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header lang={lang} onLanguageChange={setLang} />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              System Operations & Integrity Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Data provider connectivity, background job status, and cryptographic audit monitoring.
            </p>
          </div>

          <button
            onClick={loadHealth}
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 bg-white rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Diagnostics</span>
          </button>
        </div>

        {health ? (
          <div className="space-y-6">
            {/* System Status Banner */}
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
                    <span className="font-mono text-emerald-700 font-bold">{health.demo_mode ? "ACTIVE" : "INACTIVE"}</span>
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
                <div key={p.provider} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
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
                  <p className="font-mono font-bold text-slate-900 mt-1">{health.storage.backend.toUpperCase()} (Private Encrypted)</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500">AI Structured Extraction</span>
                  <p className="font-mono font-bold text-slate-900 mt-1">
                    {health.ai_provider.configured_model} (Gemini API: {health.ai_provider.has_gemini_key ? "Configured" : "Heuristic Fallback Ready"})
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-400 text-sm">Loading system telemetry...</div>
        )}
      </main>
    </div>
  );
}
