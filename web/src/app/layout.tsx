import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HeatLedger | Worker-Owned Climate Exposure & Earnings Evidence Platform",
  description: "Your work. Your conditions. Your evidence. Verifiable evidence timeline for gig and outdoor workers in Hyderabad, India.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
