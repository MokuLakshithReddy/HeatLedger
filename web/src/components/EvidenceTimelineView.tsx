import React from "react";
import { Clock, ShieldAlert, FileText, MapPin, SunMedium, Coffee, CheckCircle2 } from "lucide-react";

export interface TimelineEvent {
  id: string;
  event_category: string;
  timestamp: string;
  title: string;
  description: string;
  provenance_source: string;
  anomaly_flag?: string | null;
}

const CATEGORY_STYLES: Record<string, { bg: string; text: string; icon: any }> = {
  WORKER_ACTION: { bg: "bg-blue-100 text-blue-800", text: "Worker Action", icon: Clock },
  LOCATION_OBSERVATION: { bg: "bg-emerald-100 text-emerald-800", text: "Location Fix", icon: MapPin },
  ESTIMATED_EXPOSURE: { bg: "bg-amber-100 text-amber-800", text: "Climate Exposure", icon: SunMedium },
  WORKER_DECLARED_BREAK: { bg: "bg-teal-100 text-teal-800", text: "Worker Rest Break", icon: Coffee },
  DOCUMENT_UPLOAD: { bg: "bg-purple-100 text-purple-800", text: "Document Upload", icon: FileText },
  WORKER_CONFIRMED_VALUE: { bg: "bg-green-100 text-green-800", text: "Confirmed Earnings", icon: CheckCircle2 },
};

export function EvidenceTimelineView({ events }: { events: TimelineEvent[] }) {
  if (!events || events.length === 0) {
    return <div className="p-8 text-center text-slate-500 text-sm">No timeline events recorded.</div>;
  }

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
      {events.map((e) => {
        const cat = CATEGORY_STYLES[e.event_category] || {
          bg: "bg-slate-100 text-slate-800",
          text: e.event_category,
          icon: Clock,
        };
        const IconComponent = cat.icon;

        return (
          <div key={e.id} className="relative group">
            {/* Timeline Dot */}
            <div className="absolute -left-6 top-1.5 w-3.5 h-3.5 rounded-full border-2 border-white bg-sky-600 shadow-sm" />

            <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm hover:border-slate-300 transition">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cat.bg}`}>
                    <IconComponent className="w-3 h-3" />
                    {cat.text}
                  </span>
                  <h4 className="text-sm font-bold text-slate-900">{e.title}</h4>
                </div>
                <span className="text-xs text-slate-500 font-mono">
                  {new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              <p className="text-sm text-slate-700 leading-relaxed mb-2">{e.description}</p>

              {e.anomaly_flag && (
                <div className="mb-2 flex items-start gap-1.5 text-xs text-red-700 bg-red-50 p-2 rounded-lg border border-red-200 font-medium">
                  <ShieldAlert className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                  <span>{e.anomaly_flag}</span>
                </div>
              )}

              <div className="text-[11px] text-slate-600 font-mono flex items-center justify-between border-t border-slate-100 pt-2">
                <span>Provenance: {e.provenance_source}</span>
                <span className="text-slate-600">{new Date(e.timestamp).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
