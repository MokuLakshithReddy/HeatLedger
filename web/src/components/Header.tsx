"use client";

import Link from "next/link";
import { useState } from "react";
import { Language, translations } from "@/lib/i18n";
import { ShieldCheck, Flame, BarChart3, FolderKanban, Server, Globe } from "lucide-react";

export function Header({
  lang,
  onLanguageChange,
}: {
  lang: Language;
  onLanguageChange: (l: Language) => void;
}) {
  const t = translations[lang];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-sky-600 flex items-center justify-center text-white shadow-sm">
              <Flame className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <span className="font-bold text-lg text-slate-900 tracking-tight">HeatLedger</span>
              <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-200">
                Organisation Portal
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
            <Link href="/portal" className="flex items-center gap-1.5 hover:text-sky-600 transition">
              <FolderKanban className="w-4 h-4 text-slate-400" />
              {t.nav_cases}
            </Link>
            <Link href="/analytics" className="flex items-center gap-1.5 hover:text-sky-600 transition">
              <BarChart3 className="w-4 h-4 text-slate-400" />
              {t.nav_analytics}
            </Link>
            <Link href="/admin" className="flex items-center gap-1.5 hover:text-sky-600 transition">
              <Server className="w-4 h-4 text-slate-400" />
              {t.nav_admin}
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
            <Globe className="w-3.5 h-3.5 text-slate-500 ml-1" />
            {(['en', 'te', 'hi'] as Language[]).map((l) => (
              <button
                key={l}
                onClick={() => onLanguageChange(l)}
                className={`px-2 py-1 rounded transition uppercase ${
                  lang === l
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {l}
              </button>
            ))}
          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-xs text-amber-800 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200">
            <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
            <span className="font-medium">Hyderabad Pilot (Telangana)</span>
          </div>
        </div>
      </div>
    </header>
  );
}
