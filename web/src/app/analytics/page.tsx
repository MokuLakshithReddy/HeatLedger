"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Language, translations } from "@/lib/i18n";
import {
  BarChart3,
  ShieldCheck,
  ShieldAlert,
  Users,
  Flame,
  Info,
  Building2,
  Calendar,
} from "lucide-react";

interface CohortData {
  cohort_name: string;
  total_workers_in_cohort: number;
  meets_k_anonymity_threshold: boolean;
  k_threshold: number;
  average_heat_exposure_hours: number | null;
  average_shift_duration_hours: number | null;
  total_cases_filed: number;
  common_high_heat_time_bands: string[];
  anonymity_notice: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function AnalyticsPage() {
  const [lang, setLang] = useState<Language>("en");
  const t = translations[lang];

  const [cohort, setCohort] = useState<CohortData | null>(null);
  const [loading, setLoading] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    async function fetchAnalytics() {
      const token = typeof window !== "undefined"
        ? (sessionStorage.getItem("hl_portal_token") || sessionStorage.getItem("hl_admin_token"))
        : null;

      if (!token) {
        setNeedsAuth(true);
        setCohort({
          cohort_name: "Hyderabad Central & Hitec City Cohort (Preview)",
          total_workers_in_cohort: 4,
          meets_k_anonymity_threshold: false,
          k_threshold: 5,
          average_heat_exposure_hours: null,
          average_shift_duration_hours: null,
          total_cases_filed: 0,
          common_high_heat_time_bands: ["12:00 PM - 03:00 PM", "03:00 PM - 05:00 PM"],
          anonymity_notice: "Cohort size (k = 4) is below the minimum privacy threshold (k ≥ 5). Detailed analytics suppressed to prevent worker re-identification.",
        });
        return;
      }

      setLoading(true);
      try {
        const orgsResp = await fetch(`${API_BASE}/organisations`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (orgsResp.ok) {
          const orgs = await orgsResp.json();
          if (orgs.length > 0) {
            const orgId = orgs[0].id;
            const res = await fetch(`${API_BASE}/organisations/${orgId}/analytics`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
              const data = await res.json();
              setCohort(data);
            }
          }
        }
      } catch (err) {
        console.warn("Could not fetch live analytics:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header lang={lang} onLanguageChange={setLang} />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        <div className="mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-200 mb-3">
            <Users className="w-3.5 h-3.5 text-sky-600" />
            <span>DPDP Cohort Anonymization & Aggregation Engine</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Hyderabad Regional Heat Impact Analytics
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Aggregate occupational exposure trends for gig workers in Telangana without individual surveillance.
          </p>
        </div>

        {/* Privacy Safeguard Banner */}
        <div className="mb-8 p-4 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-start gap-3.5">
          <div className="h-9 w-9 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700 shrink-0">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              k-Anonymity Minimum Cohort Safeguard (k ≥ 5)
            </h3>
            <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
              To protect gig delivery workers against targeted platform retaliation or individual re-identification,
              granular climate and wage indicators are programmatically suppressed until at least 5 distinct consented workers
              form an active regional cohort.
            </p>
          </div>
        </div>

        {/* Cohort Card */}
        {cohort ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-5">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Target Cohort
                </span>
                <h2 className="text-xl font-bold text-slate-900 mt-0.5">
                  {cohort.cohort_name}
                </h2>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-600">Cohort Size:</span>
                <span className="text-sm font-bold text-slate-900 font-mono bg-slate-100 px-3 py-1 rounded-lg">
                  {cohort.total_workers_in_cohort} workers
                </span>
              </div>
            </div>

            {/* If threshold not met, show honest safeguard status */}
            {!cohort.meets_k_anonymity_threshold ? (
              <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300 space-y-3">
                <ShieldAlert className="w-8 h-8 text-amber-600 mx-auto" />
                <h3 className="text-base font-bold text-slate-800">
                  Individual Exposure Metrics Suppressed
                </h3>
                <p className="text-sm text-slate-600 max-w-lg mx-auto">
                  {cohort.anonymity_notice}
                </p>
                <div className="text-xs font-mono text-slate-400 mt-2">
                  Requirement: k ≥ {cohort.k_threshold} | Current consented: {cohort.total_workers_in_cohort}
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="p-5 bg-amber-50 rounded-xl border border-amber-200">
                  <span className="text-xs font-semibold text-amber-800">Avg. Severe Heat Exposure</span>
                  <p className="text-3xl font-black text-amber-950 mt-1">
                    {cohort.average_heat_exposure_hours} <span className="text-sm font-medium">hrs/week</span>
                  </p>
                  <p className="text-xs text-amber-700 mt-1 font-medium">Heat Index ≥ 39°C (Danger)</p>
                </div>

                <div className="p-5 bg-sky-50 rounded-xl border border-sky-200">
                  <span className="text-xs font-semibold text-sky-800">Avg. Shift Length</span>
                  <p className="text-3xl font-black text-sky-950 mt-1">
                    {cohort.average_shift_duration_hours} <span className="text-sm font-medium">hrs</span>
                  </p>
                  <p className="text-xs text-sky-700 mt-1 font-medium">Across active logged delivery periods</p>
                </div>

                <div className="p-5 bg-emerald-50 rounded-xl border border-emerald-200">
                  <span className="text-xs font-semibold text-emerald-800">Total Relief Cases Filed</span>
                  <p className="text-3xl font-black text-emerald-950 mt-1">
                    {cohort.total_cases_filed}
                  </p>
                  <p className="text-xs text-emerald-700 mt-1 font-medium">Under active union review</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
            {loading ? "Loading cohort intelligence..." : "No cohort metrics available."}
          </div>
        )}
      </main>
    </div>
  );
}
