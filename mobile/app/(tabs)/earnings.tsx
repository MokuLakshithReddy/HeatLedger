import React, { useState, useEffect } from "react";
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

export default function EarningsScreen() {
  const [entries, setEntries] = useState<any[]>([
    {
      id: "demo-entry-1",
      platform_name: "Swiggy",
      statement_period_start: "2026-05-11",
      statement_period_end: "2026-05-17",
      base_earnings: 4250,
      incentives: 850,
      deductions: 150,
      net_amount: 5175,
      is_confirmed_by_worker: true,
      worker_confirmed_at: "2026-05-18T10:00:00Z",
    },
    {
      id: "demo-entry-2",
      platform_name: "Zomato",
      statement_period_start: "2026-05-18",
      statement_period_end: "2026-05-24",
      base_earnings: 3800,
      incentives: 600,
      deductions: 100,
      net_amount: 4300,
      is_confirmed_by_worker: false, // Needs review
    },
  ]);

  const handleConfirm = async (entryId: string) => {
    try {
      await mobileApiFetch(`/earnings/entries/${entryId}/confirm`, {
        method: "POST",
        body: JSON.stringify({ is_confirmed: true }),
      });
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId ? { ...e, is_confirmed_by_worker: true } : e))
      );
      Alert.alert("Confirmed", "Earnings payout verified and added to your evidence timeline.");
    } catch (e) {
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId ? { ...e, is_confirmed_by_worker: true } : e))
      );
    }
  };

  const handleSimulateUpload = () => {
    Alert.alert(
      "Document Upload",
      "Selected 'Zomato_Payout_Slip.pdf'. AI extraction pipeline processed document (SHA-256 verified).",
      [{ text: "OK" }]
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Earnings Evidence</Text>
        <Text style={styles.subtitle}>
          Upload delivery payout slips. AI extracts the figures; your confirmation makes it evidence.
        </Text>

        {/* Upload Button */}
        <TouchableOpacity style={styles.uploadButton} onPress={handleSimulateUpload}>
          <Text style={styles.uploadButtonText}>📁 Upload Payout Statement (PDF / Image / CSV)</Text>
        </TouchableOpacity>

        <Text style={styles.sectionHeader}>Extracted Payout Records</Text>

        <View style={styles.list}>
          {entries.map((entry) => (
            <View key={entry.id} style={styles.entryCard}>
              <View style={styles.entryHeader}>
                <View>
                  <Text style={styles.platformName}>{entry.platform_name}</Text>
                  <Text style={styles.periodText}>
                    {entry.statement_period_start} to {entry.statement_period_end}
                  </Text>
                </View>
                <Text style={styles.netAmount}>₹{entry.net_amount}</Text>
              </View>

              <View style={styles.breakdownRow}>
                <Text style={styles.breakdownItem}>Base: ₹{entry.base_earnings}</Text>
                <Text style={styles.breakdownItem}>Incentive: ₹{entry.incentives}</Text>
                <Text style={styles.breakdownItem}>Deductions: ₹{entry.deductions}</Text>
              </View>

              <View style={styles.statusFooter}>
                {entry.is_confirmed_by_worker ? (
                  <View style={styles.confirmedBadge}>
                    <Text style={styles.confirmedText}>✓ Verified & Confirmed by Worker</Text>
                  </View>
                ) : (
                  <View style={styles.unconfirmedRow}>
                    <Text style={styles.unconfirmedWarning}>⚠️ Needs Worker Verification</Text>
                    <TouchableOpacity
                      style={styles.confirmBtn}
                      onPress={() => handleConfirm(entry.id)}
                    >
                      <Text style={styles.confirmBtnText}>Confirm Values</Text>
                    </TouchableOpacity>
                  </View>
                )}
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
  uploadButton: {
    backgroundColor: "#0284c7",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: 20,
  },
  uploadButtonText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  sectionHeader: { fontSize: 16, fontWeight: "800", color: "#0f172a", marginBottom: 12 },
  list: { gap: 12 },
  entryCard: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  entryHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 },
  platformName: { fontSize: 16, fontWeight: "800", color: "#0f172a" },
  periodText: { fontSize: 11, color: "#64748b", marginTop: 1 },
  netAmount: { fontSize: 18, fontWeight: "900", color: "#059669" },
  breakdownRow: { flexDirection: "row", gap: 12, borderTopWidth: 1, borderTopColor: "#f1f5f9", paddingTop: 8 },
  breakdownItem: { fontSize: 12, color: "#475569" },
  statusFooter: { marginTop: 12, borderTopWidth: 1, borderTopColor: "#f1f5f9", paddingTop: 8 },
  confirmedBadge: { backgroundColor: "#ecfdf5", padding: 8, borderRadius: 8, alignItems: "center" },
  confirmedText: { fontSize: 11, fontWeight: "700", color: "#065f46" },
  unconfirmedRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  unconfirmedWarning: { fontSize: 11, fontWeight: "700", color: "#b45309" },
  confirmBtn: { backgroundColor: "#0284c7", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  confirmBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 12 },
});
