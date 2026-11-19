"use client";

import { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Language, translations } from "@/lib/i18n";
import {
  ShieldCheck,
  Flame,
  FileCheck2,
  Lock,
  ArrowRight,
  TrendingDown,
  Building2,
  Smartphone,
  ChevronRight,
  Sparkles,
} from "lucide-react";

export default function HomePage() {
  const [lang, setLang] = useState<Language>("en");
  const t = translations[lang];

  return (
    <div className="min-h-screen flex flex-col">
      <Header lang={lang} onLanguageChange={setLang} />

      {/* Hero Section */}
      <main className="flex-1">
        <section className="relative overflow-hidden bg-gradient-to-b from-sky-50/60 via-white to-slate-50 border-b border-slate-200 py-16 sm:py-24">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-200 mb-6">
              <Flame className="w-3.5 h-3.5 text-amber-600" />
              <span>Hyderabad Pilot Deployment (Telangana, India)</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-black text-slate-900 tracking-tight leading-tight mb-4">
              {t.brand_name}
            </h1>
            <p className="text-xl sm:text-2xl font-semibold text-sky-700 mb-6">
              {t.tagline}
            </p>
            <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-600 leading-relaxed mb-10">
              Worker-owned climate exposure and earnings evidence platform. 
              Connecting fragmented working shifts, accredited meteorological heat observations, and verified platform earnings into an immutable, verifiable dossier.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/portal"
                className="inline-flex items-center gap-2 bg-sky-600 hover:bg-sky-700 text-white font-semibold px-6 py-3.5 rounded-xl shadow-sm transition hover:shadow-md"
              >
                <Building2 className="w-5 h-5" />
                <span>Enter Organisation Portal</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Link>
              <Link
                href="/analytics"
                className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold px-6 py-3.5 rounded-xl border border-slate-300 shadow-sm transition"
              >
                <span>View Cohort Analytics</span>
              </Link>
            </div>
          </div>
        </section>

        {/* Core Principles Grid */}
        <section className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Foundational Principles
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Designed from first principles for Indian gig delivery and outdoor transportation workers.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="h-10 w-10 rounded-xl bg-sky-100 flex items-center justify-center text-sky-700 mb-4">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Worker Data Sovereignty</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Full DPDP Act compliance. Workers hold their records. Location collection is strictly opt-in and ceases immediately when consent is revoked.
              </p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="h-10 w-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700 mb-4">
                <Flame className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Honest Climate Correlation</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Clear distinction between measured WBGT, Rothfusz Heat Index estimates, and official IMD observations. No fabricated readings during provider outages.
              </p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="h-10 w-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 mb-4">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Verifiable Dossiers</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Cryptographic SHA-256 integrity hashes on all generated PDF evidence packets, providing defensible, tamper-evident documentation for welfare claims.
              </p>
            </div>
          </div>
        </section>

        {/* Portal Access Cards */}
        <section className="bg-slate-100/70 border-t border-slate-200 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-sky-700 bg-sky-50 px-2.5 py-1 rounded-md border border-sky-100">
                    Trade Unions & Welfare Boards
                  </span>
                  <Building2 className="w-6 h-6 text-slate-400" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">Organisation Advocacy Portal</h3>
                <p className="text-sm text-slate-600 leading-relaxed mb-6">
                  Review worker-consented evidence reports, log casework notes, track extreme heat compensation claims, and review aggregated regional trends.
                </p>
                <Link
                  href="/portal"
                  className="inline-flex items-center gap-1.5 text-sm font-semibold text-sky-600 hover:text-sky-700"
                >
                  <span>Launch Portal Dashboard</span>
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>

              <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-100">
                    Mobile Application
                  </span>
                  <Smartphone className="w-6 h-6 text-slate-400" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">Worker Mobile App (Expo / React Native)</h3>
                <p className="text-sm text-slate-600 leading-relaxed mb-6">
                  One-tap shift tracking, hydration breaks, real-time heat alerts, OCR earnings extraction, and portable PDF generation in Telugu, Hindi, and English.
                </p>
                <div className="text-xs font-medium text-slate-500">
                  Target: Android / Expo Go • Location: Hyderabad Core Logistics
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
          <p>© 2026 HeatLedger Engineering Initiative. All rights reserved.</p>
          <p>Validated for Hyderabad, Telangana • English • తెలుగు • हिन्दी</p>
        </div>
      </footer>
    </div>
  );
}
