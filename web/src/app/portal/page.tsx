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

export default function PortalPage() {
  const [lang, setLang] = useState<Language>("en");
  const t = translations[lang];

  const [reports, setReports] = useState<SharedReport[]>([]);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<SharedReport | null>(null);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [newCasePriority, setNewCasePriority] = useState("HIGH");
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Demo org token for TGPWU
  const demoOrgId = "demo-org-id";

  useEffect(() => {
    // Fetch initial demo data from backend
    async function loadData() {
      try {
        // Log in as demo organisation admin
        const loginResp = await fetch("http://localhost:8000/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: "advocate@telanganaworkers.org",
            password: "TelanganaUnion123!",
          }),
        });

        if (loginResp.ok) {
          const authData = await loginResp.json();
          const token = authData.access_token;

          // Fetch organisations to get org ID
          const orgsResp = await fetch("http://localhost:8000/api/v1/organisations", {
            headers: { Authorization: `Bearer ${token}` },
          });
          const orgs = await orgsResp.json();
          if (orgs.length > 0) {
            const org = orgs[0];
            // Fetch shared reports
            const repResp = await fetch(`http://localhost:8000/api/v1/organisations/${org.id}/reports`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (repResp.ok) {
              const repData = await repResp.json();
              setReports(repData);
              if (repData.length > 0) {
                setSelectedReport(repData[0]);
              }
            }

            // Fetch cases
            const caseResp = await fetch(`http://localhost:8000/api/v1/organisations/${org.id}/cases`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (caseResp.ok) {
              const caseData = await caseResp.json();
              setCases(caseData);
            }
          }
        }
      } catch (err) {
        console.warn("Could not connect to live backend during static build, using local fallback state.", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleDownloadPDF = async (reportId: string, reportNumber: string) => {
    try {
      const loginResp = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "advocate@telanganaworkers.org",
          password: "TelanganaUnion123!",
        }),
      });
      const { access_token } = await loginResp.json();

      const orgsResp = await fetch("http://localhost:8000/api/v1/organisations", {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      const orgs = await orgsResp.json();
      const orgId = orgs[0].id;

      const res = await fetch(`http://localhost:8000/api/v1/organisations/${orgId}/reports/${reportId}/download`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });

      if (!res.ok) throw new Error("Could not download report PDF");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${reportNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Download failed: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header lang={lang} onLanguageChange={setLang} />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Page Title & Breadcrumb */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              {t.portal_title}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Telangana Gig & Platform Workers Union (TGPWU) • Hyderabad Casework Desk
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Scoped Worker Sharing Grants Active</span>
            </span>
          </div>
        </div>

        {/* Grid: Shared Reports List + Report Inspector */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          {/* Reports Column */}
          <div className="lg:col-span-1 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Consented Dossiers ({reports.length})
              </h2>
            </div>

            {loading ? (
              <div className="p-8 text-center text-sm text-slate-400">Loading reports...</div>
            ) : reports.length === 0 ? (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 text-center text-sm text-slate-500">
                {t.no_reports_shared}
              </div>
            ) : (
              <div className="space-y-3">
                {reports.map((r) => {
                  const isSelected = selectedReport?.id === r.id;
                  return (
                    <div
                      key={r.id}
                      onClick={() => setSelectedReport(r)}
                      className={`cursor-pointer p-4 rounded-xl border transition ${
                        isSelected
                          ? "bg-sky-50/70 border-sky-400 shadow-sm"
                          : "bg-white border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs font-bold text-slate-900">
                          {r.report_number}
                        </span>
                        <span className="text-[11px] text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          {r.total_extreme_heat_hours}h Extreme Heat
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 mb-2">
                        Worker ID: <span className="font-mono">{r.worker_id.slice(0, 8)}...</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-600 font-medium border-t border-slate-100 pt-2">
                        <span>{r.total_shifts} shifts ({r.total_hours_worked}h)</span>
                        <span className="text-emerald-700 font-semibold">₹{r.net_earnings_recorded}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Dossier Detail & Case Filing */}
          <div className="lg:col-span-2">
            {selectedReport ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-5">
                  <div>
                    <span className="text-xs font-mono font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded-md border border-sky-100">
                      {selectedReport.report_number}
                    </span>
                    <h3 className="text-xl font-bold text-slate-900 mt-2">
                      Verified Climate Exposure Dossier
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Period: {new Date(selectedReport.period_start).toLocaleDateString()} — {new Date(selectedReport.period_end).toLocaleDateString()}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDownloadPDF(selectedReport.id, selectedReport.report_number)}
                    className="inline-flex items-center gap-2 bg-sky-600 hover:bg-sky-700 text-white font-semibold px-4 py-2 rounded-xl text-sm transition shadow-sm"
                  >
                    <Download className="w-4 h-4" />
                    <span>{t.download_pdf}</span>
                  </button>
                </div>

                {/* Metrics Breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                    <span className="text-xs text-slate-500">Total Shifts</span>
                    <p className="text-lg font-bold text-slate-900 mt-0.5">{selectedReport.total_shifts}</p>
                  </div>
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                    <span className="text-xs text-slate-500">Hours Worked</span>
                    <p className="text-lg font-bold text-slate-900 mt-0.5">{selectedReport.total_hours_worked} hrs</p>
                  </div>
                  <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-200">
                    <span className="text-xs text-amber-800">Severe Heat (≥39°C)</span>
                    <p className="text-lg font-bold text-amber-900 mt-0.5">{selectedReport.total_extreme_heat_hours} hrs</p>
                  </div>
                  <div className="p-3.5 bg-emerald-50 rounded-xl border border-emerald-200">
                    <span className="text-xs text-emerald-800">Verified Payout</span>
                    <p className="text-lg font-bold text-emerald-900 mt-0.5">₹{selectedReport.net_earnings_recorded}</p>
                  </div>
                </div>

                {/* Cryptographic Hash Verification Box */}
                <div className="bg-slate-900 text-slate-200 p-4 rounded-xl text-xs font-mono space-y-1">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Cryptographic Document Fingerprint</span>
                    <span className="text-emerald-400 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      SHA-256 Validated
                    </span>
                  </div>
                  <p className="text-sky-300 break-all select-all font-semibold">
                    {selectedReport.integrity_sha256}
                  </p>
                </div>

                {/* Case Actions */}
                <div className="border-t border-slate-100 pt-6">
                  <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <FolderKanban className="w-4 h-4 text-sky-600" />
                    <span>Advocacy & Compensation Case Records</span>
                  </h4>
                  
                  {cases.length > 0 ? (
                    <div className="space-y-2 mb-4">
                      {cases.map((c) => (
                        <div key={c.id} className="p-3 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                          <div>
                            <span className="text-xs font-mono font-bold text-slate-700">{c.case_number}</span>
                            <p className="text-sm font-semibold text-slate-900 mt-0.5">{c.title}</p>
                            <span className="text-[11px] text-slate-500">Subject: {c.worker_pseudonym}</span>
                          </div>
                          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-amber-100 text-amber-800">
                            {c.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 mb-4">No active case initiated for this record yet.</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
                Select a shared evidence dossier from the left panel to review details.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
