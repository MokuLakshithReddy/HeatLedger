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
  Platform,
} from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { mobileApiFetch } from "@/lib/api";
import { isConsentActive } from "@/lib/consent";

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
  const [hasConsent, setHasConsent] = useState(false);

  const loadEntriesAndConsent = async () => {
    setLoading(true);
    try {
      const consents = await mobileApiFetch<any[]>("/profiles/me/consents");
      const activeConsent = isConsentActive(consents, "EARNINGS_DOCUMENT_EXTRACTION");
      setHasConsent(activeConsent);

      const data = await mobileApiFetch<EarningEntryItem[]>("/earnings/entries");
      if (Array.isArray(data)) {
        setEntries(data);
      }
    } catch (e: any) {
      console.warn("Could not load earnings entries:", e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntriesAndConsent();
  }, []);

  const handleGrantConsent = async () => {
    try {
      await mobileApiFetch("/profiles/me/consents", {
        method: "POST",
        body: JSON.stringify({
          purpose: "EARNINGS_PROCESSING",
          is_granted: true,
          consent_text_version: "1.0",
        }),
      });
      setHasConsent(true);
      Alert.alert("Consent Recorded", "Earnings extraction authorized under DPDP principles.");
    } catch (e: any) {
      Alert.alert("Consent Error", e.message || "Failed to record consent.");
    }
  };

  const handlePickAndUploadDocument = async () => {
    if (!hasConsent) {
      Alert.alert(
        "Consent Required",
        "Under the Indian DPDP Act, you must explicitly grant consent for document OCR and financial extraction before uploading statements.",
        [
          { text: "Cancel", style: "cancel" },
          { text: "Grant Consent", onPress: handleGrantConsent },
        ]
      );
      return;
    }

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          "application/pdf",
          "image/png",
          "image/jpeg",
          "image/jpg",
          "text/csv",
        ],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) {
        return;
      }

      const asset = result.assets[0];
      setUploading(true);

      const formData = new FormData();
      if (Platform.OS === "web") {
        if (asset.file) {
          formData.append("file", asset.file);
        } else {
          const resp = await fetch(asset.uri);
          const blob = await resp.blob();
          formData.append("file", blob, asset.name);
        }
      } else {
        formData.append("file", {
          uri: asset.uri,
          name: asset.name,
          type: asset.mimeType || "application/octet-stream",
        } as any);
      }

      await mobileApiFetch("/earnings/uploads", {
        method: "POST",
        body: formData,
      });

      Alert.alert(
        "Statement Ingested",
        `Successfully extracted financial figures from ${asset.name}. Review and confirm below.`
      );
      await loadEntriesAndConsent();
    } catch (err: any) {
      Alert.alert("Upload Failed", err.message || "Could not process document.");
    } finally {
      setUploading(false);
    }
  };

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

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Earnings Evidence</Text>
        <Text style={styles.subtitle}>
          Upload delivery slips (PDF, PNG, JPG, CSV). AI and deterministic OCR extract base pay, tips, and deductions.
        </Text>

        {/* Consent Status Banner */}
        {!hasConsent && (
          <View style={styles.consentWarningCard}>
            <Text style={styles.consentWarningTitle}>🔒 Processing Consent Required</Text>
            <Text style={styles.consentWarningText}>
              In accordance with DPDP rules, financial document extraction requires your prior explicit authorization.
            </Text>
            <TouchableOpacity style={styles.grantConsentBtn} onPress={handleGrantConsent}>
              <Text style={styles.grantConsentBtnText}>Authorize Earnings Document Extraction</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Upload Action Card */}
        <View style={styles.uploadCard}>
          <Text style={styles.uploadTitle}>Upload Platform Payout Statement</Text>
          <Text style={styles.uploadSubtitle}>
            Supported: Swiggy, Zomato, Porter, Uber (PDF, JPG, PNG, CSV) • Max 10MB
          </Text>

          <TouchableOpacity
            style={styles.chooseFileBtn}
            onPress={handlePickAndUploadDocument}
            disabled={uploading}
          >
            {uploading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.chooseFileBtnText}>📁 Select Payout Document / Slip</Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Verified vs Unconfirmed Entries */}
        <Text style={styles.sectionTitle}>Extracted Payout Records</Text>

        {loading ? (
          <ActivityIndicator color="#0284c7" style={{ marginVertical: 20 }} />
        ) : entries.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>No Statements Processed</Text>
            <Text style={styles.emptySubtitle}>
              Upload your weekly delivery statements to document pay and correlate against severe heat.
            </Text>
          </View>
        ) : (
          entries.map((item) => (
            <View key={item.id} style={styles.entryCard}>
              <View style={styles.entryHeader}>
                <View>
                  <Text style={styles.entryPlatform}>{item.platform_name}</Text>
                  <Text style={styles.entryPeriod}>
                    {new Date(item.statement_period_start).toLocaleDateString()} -{" "}
                    {new Date(item.statement_period_end).toLocaleDateString()}
                  </Text>
                </View>
                <View
                  style={[
                    styles.statusBadge,
                    item.is_confirmed_by_worker ? styles.statusConfirmed : styles.statusPending,
                  ]}
                >
                  <Text
                    style={[
                      styles.statusBadgeText,
                      item.is_confirmed_by_worker ? styles.textConfirmed : styles.textPending,
                    ]}
                  >
                    {item.is_confirmed_by_worker ? "Worker Verified" : "Needs Review"}
                  </Text>
                </View>
              </View>

              <View style={styles.breakdownRow}>
                <View style={styles.breakdownItem}>
                  <Text style={styles.breakdownLabel}>Base Pay</Text>
                  <Text style={styles.breakdownValue}>₹{item.base_earnings.toFixed(2)}</Text>
                </View>
                <View style={styles.breakdownItem}>
                  <Text style={styles.breakdownLabel}>Incentives</Text>
                  <Text style={styles.breakdownValue}>₹{item.incentives.toFixed(2)}</Text>
                </View>
                <View style={styles.breakdownItem}>
                  <Text style={styles.breakdownLabel}>Deductions</Text>
                  <Text style={[styles.breakdownValue, styles.textDeduction]}>
                    -₹{item.deductions.toFixed(2)}
                  </Text>
                </View>
                <View style={styles.breakdownItem}>
                  <Text style={styles.breakdownLabel}>Net Payout</Text>
                  <Text style={[styles.breakdownValue, styles.textNet]}>
                    ₹{item.net_amount.toFixed(2)}
                  </Text>
                </View>
              </View>

              {!item.is_confirmed_by_worker && (
                <View style={styles.confirmPrompt}>
                  <Text style={styles.confirmNotice}>
                    ⚠️ Unconfirmed figures are excluded from official union evidence dossiers.
                  </Text>
                  <TouchableOpacity
                    style={styles.confirmBtn}
                    onPress={() => handleConfirm(item.id)}
                  >
                    <Text style={styles.confirmBtnText}>✓ Verify Figures Match Platform Statement</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          ))
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
  consentWarningCard: {
    backgroundColor: "#fffbeb",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#fde68a",
    marginBottom: 16,
  },
  consentWarningTitle: { fontSize: 14, fontWeight: "800", color: "#b45309", marginBottom: 4 },
  consentWarningText: { fontSize: 12, color: "#78350f", marginBottom: 12 },
  grantConsentBtn: { backgroundColor: "#b45309", paddingVertical: 10, borderRadius: 8, alignItems: "center" },
  grantConsentBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 12 },
  uploadCard: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginBottom: 20,
  },
  uploadTitle: { fontSize: 15, fontWeight: "800", color: "#0f172a" },
  uploadSubtitle: { fontSize: 12, color: "#64748b", marginTop: 2, marginBottom: 14 },
  chooseFileBtn: {
    backgroundColor: "#0284c7",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  chooseFileBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  sectionTitle: { fontSize: 16, fontWeight: "800", color: "#0f172a", marginBottom: 12 },
  emptyCard: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 24,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    alignItems: "center",
  },
  emptyTitle: { fontSize: 14, fontWeight: "700", color: "#334155" },
  emptySubtitle: { fontSize: 12, color: "#94a3b8", textAlign: "center", marginTop: 4 },
  entryCard: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginBottom: 12,
  },
  entryHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  entryPlatform: { fontSize: 15, fontWeight: "800", color: "#0f172a" },
  entryPeriod: { fontSize: 11, color: "#64748b", marginTop: 1 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  statusConfirmed: { backgroundColor: "#dcfce7" },
  statusPending: { backgroundColor: "#fef3c7" },
  statusBadgeText: { fontSize: 11, fontWeight: "700" },
  textConfirmed: { color: "#166534" },
  textPending: { color: "#b45309" },
  breakdownRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8, borderTopWidth: 1, borderTopColor: "#f1f5f9" },
  breakdownItem: { alignItems: "center" },
  breakdownLabel: { fontSize: 10, color: "#94a3b8", fontWeight: "600" },
  breakdownValue: { fontSize: 13, fontWeight: "800", color: "#334155", marginTop: 2 },
  textDeduction: { color: "#dc2626" },
  textNet: { color: "#059669" },
  confirmPrompt: { marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: "#f1f5f9" },
  confirmNotice: { fontSize: 11, color: "#b45309", marginBottom: 8 },
  confirmBtn: { backgroundColor: "#10b981", paddingVertical: 10, borderRadius: 8, alignItems: "center" },
  confirmBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 12 },
});
