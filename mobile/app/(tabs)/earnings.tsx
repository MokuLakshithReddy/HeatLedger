import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  TextInput,
} from "react-native";
import { mobileApiFetch } from "@/lib/api";

interface EarningEntryItem {
  id: string;
  platform_name: string;
  statement_period_start: string;
  statement_period_end: string;
  base_earnings: number;
  incentives: number;
  deductions: number;
  net_amount: number;
  is_confirmed_by_worker: boolean;
  worker_confirmed_at?: string;
  source_attribution_notes?: string;
}

export default function EarningsScreen() {
  const [entries, setEntries] = useState<EarningEntryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showCsvInput, setShowCsvInput] = useState(false);
  const [csvContent, setCsvContent] = useState(
    "Date | Platform | Base Pay | Incentives | Deductions | Net Payout\n2026-05-18 | Swiggy | 4200.00 | 850.00 | 120.00 | 4930.00"
  );

  const loadEntries = async () => {
    setLoading(true);
    try {
      const data = await mobileApiFetch<EarningEntryItem[]>("/earnings/entries");
      setEntries(data);
    } catch (e: any) {
      console.warn("Could not load earnings entries:", e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntries();
  }, []);

  const handleConfirm = async (entryId: string) => {
    try {
      await mobileApiFetch(`/earnings/entries/${entryId}/confirm`, {
        method: "POST",
        body: JSON.stringify({ is_confirmed: true }),
      });
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId ? { ...e, is_confirmed_by_worker: true } : e))
      );
      Alert.alert("Verified", "Earnings payout verified and confirmed into your evidence dossier.");
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to confirm entry.");
    }
  };

  const handleUploadCsv = async () => {
    if (!csvContent.trim()) {
      Alert.alert("Empty Statement", "Please enter or paste statement CSV content.");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      const blob = new Blob([csvContent], { type: "text/csv" });
      formData.append("file", blob, "payout_statement.csv");

      await mobileApiFetch("/earnings/uploads", {
        method: "POST",
        body: formData,
      });

      Alert.alert("Upload Processed", "Statement extracted successfully. Review and confirm the figures below.");
      setShowCsvInput(false);
      await loadEntries();
    } catch (e: any) {
      Alert.alert("Upload Failed", e.message || "Could not process statement.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Earnings Evidence</Text>
        <Text style={styles.subtitle}>
          Upload delivery payout slips. AI extracts the figures; your explicit confirmation makes it verifiable evidence.
        </Text>

        <View style={styles.uploadCard}>
          <Text style={styles.uploadCardTitle}>Add Platform Statement</Text>
          <Text style={styles.uploadCardDesc}>
            Upload your weekly Swiggy, Zomato, Porter, or Uber payout statement (CSV or text-based PDF).
          </Text>

          {showCsvInput ? (
            <View style={{ marginTop: 12 }}>
              <Text style={styles.label}>Paste Statement CSV Data</Text>
              <TextInput
                style={styles.csvInput}
                multiline
                numberOfLines={4}
                value={csvContent}
                onChangeText={setCsvContent}
                placeholder="Paste CSV statement lines..."
                editable={!uploading}
              />
              <View style={{ flexDirection: "row", gap: 8, marginTop: 10 }}>
                <TouchableOpacity
                  style={[styles.uploadButton, { flex: 1 }]}
                  onPress={handleUploadCsv}
                  disabled={uploading}
                >
                  {uploading ? (
                    <ActivityIndicator color="#ffffff" />
                  ) : (
                    <Text style={styles.uploadButtonText}>Submit for Extraction</Text>
                  )}
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.cancelButton, { flex: 1 }]}
                  onPress={() => setShowCsvInput(false)}
                  disabled={uploading}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.uploadButton}
              onPress={() => setShowCsvInput(true)}
            >
              <Text style={styles.uploadButtonText}>+ Upload Statement</Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.headerRow}>
          <Text style={styles.sectionTitle}>Recorded Payouts</Text>
          <TouchableOpacity onPress={loadEntries}>
            <Text style={styles.refreshLink}>Refresh</Text>
          </TouchableOpacity>
        </View>

        {loading ? (
          <ActivityIndicator color="#f97316" style={{ marginTop: 20 }} />
        ) : entries.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>No earnings statements uploaded yet.</Text>
            <Text style={styles.emptySubtext}>Uploaded statements will appear here for review and confirmation.</Text>
          </View>
        ) : (
          entries.map((entry) => (
            <View key={entry.id} style={styles.entryCard}>
              <View style={styles.entryHeader}>
                <Text style={styles.platformName}>{entry.platform_name}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    entry.is_confirmed_by_worker ? styles.statusConfirmed : styles.statusReview,
                  ]}
                >
                  <Text
                    style={[
                      styles.statusBadgeText,
                      entry.is_confirmed_by_worker ? styles.statusConfirmedText : styles.statusReviewText,
                    ]}
                  >
                    {entry.is_confirmed_by_worker ? "✓ Confirmed Evidence" : "⚠️ Needs Worker Review"}
                  </Text>
                </View>
              </View>

              <Text style={styles.periodText}>
                Period: {entry.statement_period_start.slice(0, 10)} to {entry.statement_period_end.slice(0, 10)}
              </Text>

              <View style={styles.grid}>
                <View style={styles.gridItem}>
                  <Text style={styles.gridLabel}>Base Pay</Text>
                  <Text style={styles.gridValue}>₹{entry.base_earnings}</Text>
                </View>
                <View style={styles.gridItem}>
                  <Text style={styles.gridLabel}>Incentives</Text>
                  <Text style={styles.gridValue}>₹{entry.incentives}</Text>
                </View>
                <View style={styles.gridItem}>
                  <Text style={styles.gridLabel}>Deductions</Text>
                  <Text style={styles.gridValue}>-₹{entry.deductions}</Text>
                </View>
                <View style={styles.gridItem}>
                  <Text style={styles.gridLabel}>Net Payout</Text>
                  <Text style={[styles.gridValue, styles.netValue]}>₹{entry.net_amount}</Text>
                </View>
              </View>

              {!entry.is_confirmed_by_worker && (
                <TouchableOpacity
                  style={styles.confirmButton}
                  onPress={() => handleConfirm(entry.id)}
                >
                  <Text style={styles.confirmButtonText}>Verify & Confirm Figures</Text>
                </TouchableOpacity>
              )}
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#0f172a" },
  container: { padding: 16 },
  title: { fontSize: 24, fontWeight: "800", color: "#f8fafc", marginBottom: 4 },
  subtitle: { fontSize: 13, color: "#94a3b8", marginBottom: 16, lineHeight: 18 },
  uploadCard: { backgroundColor: "#1e293b", padding: 16, borderRadius: 12, marginBottom: 20, borderWidth: 1, borderColor: "#334155" },
  uploadCardTitle: { fontSize: 16, fontWeight: "700", color: "#f8fafc", marginBottom: 4 },
  uploadCardDesc: { fontSize: 12, color: "#94a3b8", marginBottom: 12 },
  label: { fontSize: 12, fontWeight: "600", color: "#cbd5e1", marginBottom: 6 },
  csvInput: { backgroundColor: "#0f172a", borderWidth: 1, borderColor: "#334155", borderRadius: 8, padding: 8, color: "#f8fafc", fontSize: 12, minHeight: 80 },
  uploadButton: { backgroundColor: "#f97316", padding: 12, borderRadius: 8, alignItems: "center" },
  uploadButtonText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  cancelButton: { backgroundColor: "#334155", padding: 12, borderRadius: 8, alignItems: "center" },
  cancelButtonText: { color: "#cbd5e1", fontWeight: "600", fontSize: 14 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: "#f8fafc" },
  refreshLink: { color: "#38bdf8", fontSize: 13, fontWeight: "600" },
  emptyCard: { backgroundColor: "#1e293b", padding: 24, borderRadius: 12, alignItems: "center" },
  emptyText: { color: "#94a3b8", fontSize: 14, fontWeight: "600" },
  emptySubtext: { color: "#64748b", fontSize: 12, marginTop: 4, textAlign: "center" },
  entryCard: { backgroundColor: "#1e293b", padding: 16, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: "#334155" },
  entryHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  platformName: { fontSize: 16, fontWeight: "700", color: "#f8fafc" },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  statusConfirmed: { backgroundColor: "rgba(16, 185, 129, 0.15)" },
  statusReview: { backgroundColor: "rgba(245, 158, 11, 0.15)" },
  statusBadgeText: { fontSize: 11, fontWeight: "700" },
  statusConfirmedText: { color: "#34d399" },
  statusReviewText: { color: "#fbbf24" },
  periodText: { fontSize: 12, color: "#94a3b8", marginBottom: 12 },
  grid: { flexDirection: "row", justifyContent: "space-between", marginBottom: 12 },
  gridItem: { flex: 1 },
  gridLabel: { fontSize: 11, color: "#64748b", marginBottom: 2 },
  gridValue: { fontSize: 14, fontWeight: "600", color: "#cbd5e1" },
  netValue: { color: "#38bdf8", fontWeight: "700" },
  confirmButton: { backgroundColor: "#0284c7", padding: 10, borderRadius: 8, alignItems: "center", marginTop: 4 },
  confirmButtonText: { color: "#ffffff", fontWeight: "700", fontSize: 13 },
});
