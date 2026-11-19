import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  Alert,
} from "react-native";
import { mobileApiFetch } from "@/lib/api";

export default function ReportsScreen() {
  const [reports, setReports] = useState<any[]>([
    {
      id: "demo-report-1",
      report_number: "HL-HYD-20260518-75567D",
      period: "May 11 - May 18, 2026",
      shifts: 6,
      hours: 38.5,
      extreme_heat_hours: 14.0,
      earnings: 5175.0,
      sha256: "68ea4e1bdfdaef7f830a6c2f9011de...",
      is_shared: true,
    },
  ]);

  const [timelineEvents, setTimelineEvents] = useState<any[]>([
    {
      id: "1",
      time: "10:00 AM",
      title: "Shift Started",
      category: "Worker Action",
      desc: "Swiggy & Zomato shift logged. Location tracking enabled.",
    },
    {
      id: "2",
      time: "01:30 PM",
      title: "Extreme Heat Index (48.2°C)",
      category: "Climate Exposure",
      desc: "Begumpet station reported 41.5°C with 38% RH. Extreme Danger threshold.",
    },
    {
      id: "3",
      time: "01:45 PM",
      title: "Hydration Rest Break",
      category: "Worker Declared Break",
      desc: "20 min rest at shaded booth in Hitec City.",
    },
    {
      id: "4",
      time: "05:00 PM",
      title: "Shift Ended",
      category: "Worker Action",
      desc: "Total working time: 6 hrs 15 mins. Breaks: 45 mins.",
    },
  ]);

  const handleGenerateReport = async () => {
    Alert.alert(
      "Report Generated",
      "Evidence Dossier compiled with SHA-256 integrity hash. You can share this with your union.",
      [{ text: "OK" }]
    );
  };

  const handleToggleShare = (reportId: string) => {
    setReports((prev) =>
      prev.map((r) => {
        if (r.id === reportId) {
          const newState = !r.is_shared;
          Alert.alert(
            newState ? "Access Granted" : "Access Revoked",
            newState
              ? "Shared with Telangana Gig Workers Union (TGPWU) for casework review."
              : "Union access revoked immediately. Future access is blocked."
          );
          return { ...r, is_shared: newState };
        }
        return r;
      })
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Evidence Dossiers</Text>
        <Text style={styles.subtitle}>
          Correlate shifts, temperature stress, and payouts into verifiable legal records.
        </Text>

        {/* Generate Report Button */}
        <TouchableOpacity style={styles.generateBtn} onPress={handleGenerateReport}>
          <Text style={styles.generateBtnText}>⚡ Generate New 7-Day Evidence Report</Text>
        </TouchableOpacity>

        {/* Reports List */}
        <Text style={styles.sectionTitle}>Generated Dossiers</Text>
        <View style={styles.reportsList}>
          {reports.map((r) => (
            <View key={r.id} style={styles.reportCard}>
              <View style={styles.reportHeader}>
                <View>
                  <Text style={styles.reportNum}>{r.report_number}</Text>
                  <Text style={styles.reportPeriod}>{r.period}</Text>
                </View>
                <View style={styles.shaBadge}>
                  <Text style={styles.shaBadgeText}>SHA-256 Signed</Text>
                </View>
              </View>

              <View style={styles.metricsSummary}>
                <Text style={styles.summaryItem}>Shifts: {r.shifts}</Text>
                <Text style={styles.summaryItem}>Total: {r.hours}h</Text>
                <Text style={styles.summaryItem}>🔥 Severe Heat: {r.extreme_heat_hours}h</Text>
                <Text style={styles.summaryItem}>₹{r.earnings}</Text>
              </View>

              <View style={styles.hashBox}>
                <Text style={styles.hashLabel}>Integrity Fingerprint:</Text>
                <Text style={styles.hashText}>{r.sha256}</Text>
              </View>

              <View style={styles.actionsRow}>
                <TouchableOpacity
                  style={[styles.shareBtn, r.is_shared ? styles.revokeBtn : styles.grantBtn]}
                  onPress={() => handleToggleShare(r.id)}
                >
                  <Text style={styles.shareBtnText}>
                    {r.is_shared ? "Revoke Union Access" : "Share with TGPWU Union"}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.downloadBtn}
                  onPress={() => Alert.alert("PDF Download", "PDF file downloaded to device storage.")}
                >
                  <Text style={styles.downloadBtnText}>Download PDF</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))}
        </View>

        {/* Evidence Timeline */}
        <Text style={styles.sectionTitle}>Correlated Timeline Sample</Text>
        <View style={styles.timelineList}>
          {timelineEvents.map((e) => (
            <View key={e.id} style={styles.timelineItem}>
              <View style={styles.timelineDot} />
              <View style={styles.timelineContent}>
                <View style={styles.timelineItemHeader}>
                  <Text style={styles.timelineItemTitle}>{e.title}</Text>
                  <Text style={styles.timelineTime}>{e.time}</Text>
                </View>
                <Text style={styles.timelineCategory}>{e.category}</Text>
                <Text style={styles.timelineDesc}>{e.desc}</Text>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f8fafc" },
  container: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: "900", color: "#0f172a" },
  subtitle: { fontSize: 13, color: "#64748b", marginTop: 4, marginBottom: 16 },
  generateBtn: {
    backgroundColor: "#0284c7",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: 20,
  },
  generateBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  sectionTitle: { fontSize: 16, fontWeight: "800", color: "#0f172a", marginBottom: 12 },
  reportsList: { gap: 12, marginBottom: 24 },
  reportCard: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  reportHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 },
  reportNum: { fontSize: 14, fontWeight: "800", color: "#0f172a" },
  reportPeriod: { fontSize: 11, color: "#64748b" },
  shaBadge: { backgroundColor: "#dcfce7", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  shaBadgeText: { fontSize: 10, fontWeight: "700", color: "#166534" },
  metricsSummary: { flexDirection: "row", justifyContent: "space-between", marginVertical: 8 },
  summaryItem: { fontSize: 11, fontWeight: "600", color: "#334155" },
  hashBox: { backgroundColor: "#f8fafc", padding: 8, borderRadius: 6, marginVertical: 8 },
  hashLabel: { fontSize: 10, color: "#94a3b8" },
  hashText: { fontSize: 10, fontFamily: "monospace", color: "#0284c7" },
  actionsRow: { flexDirection: "row", gap: 10, marginTop: 6 },
  shareBtn: { flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: "center" },
  grantBtn: { backgroundColor: "#0284c7" },
  revokeBtn: { backgroundColor: "#dc2626" },
  shareBtnText: { color: "#ffffff", fontSize: 11, fontWeight: "700" },
  downloadBtn: { backgroundColor: "#f1f5f9", paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  downloadBtnText: { color: "#334155", fontSize: 11, fontWeight: "700" },
  timelineList: { paddingLeft: 8 },
  timelineItem: { flexDirection: "row", gap: 12, marginBottom: 16 },
  timelineDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: "#0284c7", marginTop: 4 },
  timelineContent: { flex: 1, backgroundColor: "#ffffff", padding: 12, borderRadius: 10, borderWidth: 1, borderColor: "#e2e8f0" },
  timelineItemHeader: { flexDirection: "row", justifyContent: "space-between" },
  timelineItemTitle: { fontSize: 13, fontWeight: "700", color: "#0f172a" },
  timelineTime: { fontSize: 11, color: "#94a3b8" },
  timelineCategory: { fontSize: 10, fontWeight: "700", color: "#0284c7", marginVertical: 2 },
  timelineDesc: { fontSize: 12, color: "#64748b", marginTop: 2 },
});
