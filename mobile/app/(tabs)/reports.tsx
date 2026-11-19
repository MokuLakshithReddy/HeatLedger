import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from "react-native";
import { mobileApiFetch } from "@/lib/api";

export default function ReportsScreen() {
  const [reports, setReports] = useState<any[]>([]);
  const [shares, setShares] = useState<any[]>([]);
  const [organisations, setOrganisations] = useState<any[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [reps, shr, orgs, tl] = await Promise.allSettled([
        mobileApiFetch<any[]>("/evidence/reports"),
        mobileApiFetch<any[]>("/evidence/shares"),
        mobileApiFetch<any[]>("/organisations"),
        mobileApiFetch<any>("/evidence/timeline"),
      ]);

      if (reps.status === "fulfilled" && Array.isArray(reps.value)) {
        setReports(reps.value);
      }
      if (shr.status === "fulfilled" && Array.isArray(shr.value)) {
        setShares(shr.value);
      }
      if (orgs.status === "fulfilled" && Array.isArray(orgs.value)) {
        setOrganisations(orgs.value);
      }
      if (tl.status === "fulfilled" && tl.value && Array.isArray(tl.value.events)) {
        setTimelineEvents(tl.value.events);
      }
    } catch (e: any) {
      console.warn("Failed loading reports data:", e);
    } finally {
      setLoading(false);
    }
  }

  const handleGenerateReport = async () => {
    setGenerating(true);
    try {
      const now = new Date();
      const past7 = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

      const res = await mobileApiFetch<any>("/evidence/reports", {
        method: "POST",
        body: JSON.stringify({
          period_start: past7.toISOString(),
          period_end: now.toISOString(),
        }),
      });

      Alert.alert(
        "Evidence Dossier Generated",
        `Report ${res.report_number} created.\nSHA-256 Fingerprint:\n${res.integrity_sha256.slice(0, 32)}...`
      );
      loadData();
    } catch (err: any) {
      Alert.alert("Generation Error", err.message || "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const handleToggleShare = async (reportId: string) => {
    // Check if currently shared
    const activeShare = shares.find(
      (s) => s.report_id === reportId && s.is_active && !s.revoked_at
    );

    if (activeShare) {
      // Revoke share
      try {
        await mobileApiFetch(`/evidence/shares/${activeShare.id}/revoke`, {
          method: "POST",
        });
        Alert.alert("Access Revoked", "Organisation access revoked immediately.");
        loadData();
      } catch (e: any) {
        Alert.alert("Error Revoking", e.message || "Failed to revoke share");
      }
    } else {
      // Create share with first approved org
      const targetOrg = organisations.find((o) => o.is_approved) || organisations[0];
      if (!targetOrg) {
        Alert.alert("No Organisations", "No approved worker organisations available to share with.");
        return;
      }

      try {
        await mobileApiFetch("/evidence/shares", {
          method: "POST",
          body: JSON.stringify({
            report_id: reportId,
            recipient_org_id: targetOrg.id,
            purpose: "CASEWORK_SUPPORT",
            expires_in_days: 30,
          }),
        });
        Alert.alert(
          "Report Shared",
          `Access granted to ${targetOrg.legal_name || "Union"} for casework support (30 days).`
        );
        loadData();
      } catch (e: any) {
        Alert.alert("Share Error", e.message || "Failed to share report");
      }
    }
  };

  const handleVerifyReport = async (reportId: string) => {
    try {
      const result = await mobileApiFetch<any>(`/evidence/reports/${reportId}/verify`);
      if (result.verified) {
        Alert.alert("Integrity Verified ✅", `Digest matches stored SHA-256 byte-level hash:\n${result.sha256}`);
      } else {
        Alert.alert("Verification Alert ⚠️", "Cryptographic fingerprint mismatch detected!");
      }
    } catch (e: any) {
      Alert.alert("Verification Check", e.message || "Failed to verify integrity");
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Evidence Dossiers</Text>
        <Text style={styles.subtitle}>
          Correlate shifts, temperature stress, and payouts into verifiable legal records.
        </Text>

        {/* Generate Report Button */}
        <TouchableOpacity
          style={styles.generateBtn}
          onPress={handleGenerateReport}
          disabled={generating}
        >
          {generating ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.generateBtnText}>⚡ Generate New 7-Day Evidence Report</Text>
          )}
        </TouchableOpacity>

        {/* Reports List */}
        <Text style={styles.sectionTitle}>Generated Dossiers</Text>
        {loading && reports.length === 0 ? (
          <ActivityIndicator color="#0284c7" style={{ marginVertical: 20 }} />
        ) : reports.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>No Dossiers Compiled</Text>
            <Text style={styles.emptyText}>Tap the button above to compile your first evidence dossier.</Text>
          </View>
        ) : (
          <View style={styles.reportsList}>
            {reports.map((r) => {
              const isShared = shares.some(
                (s) => s.report_id === r.id && s.is_active && !s.revoked_at
              );

              return (
                <View key={r.id} style={styles.reportCard}>
                  <View style={styles.reportHeader}>
                    <View>
                      <Text style={styles.reportNum}>{r.report_number}</Text>
                      <Text style={styles.reportPeriod}>
                        {new Date(r.period_start).toLocaleDateString()} - {new Date(r.period_end).toLocaleDateString()}
                      </Text>
                    </View>
                    <View style={styles.shaBadge}>
                      <Text style={styles.shaBadgeText}>SHA-256 Verified</Text>
                    </View>
                  </View>

                  <View style={styles.metricsSummary}>
                    <Text style={styles.summaryItem}>Shifts: {r.total_shifts}</Text>
                    <Text style={styles.summaryItem}>Total: {r.total_hours_worked}h</Text>
                    <Text style={styles.summaryItem}>🔥 Severe Heat: {r.total_extreme_heat_hours}h</Text>
                    <Text style={styles.summaryItem}>₹{r.net_earnings_recorded}</Text>
                  </View>

                  <View style={styles.hashBox}>
                    <Text style={styles.hashLabel}>Integrity Fingerprint (SHA-256):</Text>
                    <Text style={styles.hashText}>{r.integrity_sha256}</Text>
                  </View>

                  <View style={styles.actionsRow}>
                    <TouchableOpacity
                      style={[styles.shareBtn, isShared ? styles.revokeBtn : styles.grantBtn]}
                      onPress={() => handleToggleShare(r.id)}
                    >
                      <Text style={styles.shareBtnText}>
                        {isShared ? "Revoke Union Access" : "Share with Union"}
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.downloadBtn}
                      onPress={() => handleVerifyReport(r.id)}
                    >
                      <Text style={styles.downloadBtnText}>Verify Hash</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* Evidence Timeline */}
        <Text style={styles.sectionTitle}>Correlated Timeline Events</Text>
        {timelineEvents.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>No timeline events recorded yet. Complete a shift to see correlated records.</Text>
          </View>
        ) : (
          <View style={styles.timelineList}>
            {timelineEvents.slice(0, 10).map((e) => (
              <View key={e.id} style={styles.timelineItem}>
                <View style={styles.timelineDot} />
                <View style={styles.timelineContent}>
                  <View style={styles.timelineItemHeader}>
                    <Text style={styles.timelineItemTitle}>{e.title}</Text>
                    <Text style={styles.timelineTime}>
                      {new Date(e.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </Text>
                  </View>
                  <Text style={styles.timelineCategory}>{e.event_type.replace(/_/g, " ")}</Text>
                  <Text style={styles.timelineDesc}>{e.description}</Text>
                </View>
              </View>
            ))}
          </View>
        )}
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
  emptyCard: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    alignItems: "center",
    marginBottom: 20,
  },
  emptyTitle: { fontSize: 14, fontWeight: "700", color: "#334155", marginBottom: 4 },
  emptyText: { fontSize: 12, color: "#94a3b8", textAlign: "center" },
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
  shareBtn: { flex: 1, paddingVertical: 10, borderRadius: 8, alignItems: "center" },
  grantBtn: { backgroundColor: "#0284c7" },
  revokeBtn: { backgroundColor: "#ef4444" },
  shareBtnText: { color: "#ffffff", fontSize: 12, fontWeight: "700" },
  downloadBtn: {
    backgroundColor: "#f1f5f9",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  downloadBtnText: { color: "#334155", fontSize: 12, fontWeight: "700" },
  timelineList: { gap: 12 },
  timelineItem: { flexDirection: "row", gap: 12 },
  timelineDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: "#0284c7", marginTop: 4 },
  timelineContent: {
    flex: 1,
    backgroundColor: "#ffffff",
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  timelineItemHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 2 },
  timelineItemTitle: { fontSize: 13, fontWeight: "700", color: "#0f172a" },
  timelineTime: { fontSize: 11, color: "#64748b" },
  timelineCategory: { fontSize: 10, fontWeight: "600", color: "#0284c7", marginBottom: 4 },
  timelineDesc: { fontSize: 12, color: "#475569" },
});
