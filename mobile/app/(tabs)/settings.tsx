import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  Switch,
  Alert,
} from "react-native";
import { router } from "expo-router";
import { mobileApiFetch } from "@/lib/api";
import { SessionStore } from "@/lib/store";

export default function SettingsScreen() {
  const [locationConsent, setLocationConsent] = useState(true);
  const [earningsConsent, setEarningsConsent] = useState(true);
  const [researchConsent, setResearchConsent] = useState(false);
  const [selectedLang, setSelectedLang] = useState("te");

  useEffect(() => {
    async function loadConsents() {
      try {
        const consents = await mobileApiFetch<any[]>("/profiles/me/consents");
        if (Array.isArray(consents)) {
          for (const c of consents) {
            if (c.purpose === "LOCATION_TRACKING_DURING_SHIFT") setLocationConsent(c.is_granted);
            if (c.purpose === "EARNINGS_PROCESSING") setEarningsConsent(c.is_granted);
            if (c.purpose === "ANONYMIZED_RESEARCH") setResearchConsent(c.is_granted);
          }
        }
      } catch (e) {
        console.warn("Could not load user consents", e);
      }
    }
    loadConsents();
  }, []);

  const handleToggleLocation = async (val: boolean) => {
    setLocationConsent(val);
    try {
      if (val) {
        await mobileApiFetch("/profiles/me/consents", {
          method: "POST",
          body: JSON.stringify({ purpose: "LOCATION_TRACKING_DURING_SHIFT", is_granted: true }),
        });
        Alert.alert("Consent Updated", "Location tracking permitted during active shifts only.");
      } else {
        await mobileApiFetch("/profiles/me/consents/revoke", {
          method: "POST",
          body: JSON.stringify({ purpose: "LOCATION_TRACKING_DURING_SHIFT" }),
        });
        Alert.alert(
          "Consent Revoked",
          "Location collection ceased immediately. Ongoing shifts have tracking disabled."
        );
      }
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to update consent");
    }
  };

  const handleToggleEarnings = async (val: boolean) => {
    setEarningsConsent(val);
    try {
      if (val) {
        await mobileApiFetch("/profiles/me/consents", {
          method: "POST",
          body: JSON.stringify({ purpose: "EARNINGS_PROCESSING", is_granted: true }),
        });
        Alert.alert("Consent Updated", "Earnings statement processing permitted.");
      } else {
        await mobileApiFetch("/profiles/me/consents/revoke", {
          method: "POST",
          body: JSON.stringify({ purpose: "EARNINGS_PROCESSING" }),
        });
        Alert.alert("Consent Revoked", "Earnings processing consent revoked.");
      }
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to update consent");
    }
  };

  const handleToggleResearch = async (val: boolean) => {
    setResearchConsent(val);
    try {
      if (val) {
        await mobileApiFetch("/profiles/me/consents", {
          method: "POST",
          body: JSON.stringify({ purpose: "ANONYMIZED_RESEARCH", is_granted: true }),
        });
      } else {
        await mobileApiFetch("/profiles/me/consents/revoke", {
          method: "POST",
          body: JSON.stringify({ purpose: "ANONYMIZED_RESEARCH" }),
        });
      }
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to update consent");
    }
  };

  const handleExportData = async () => {
    try {
      const data = await mobileApiFetch("/profiles/me/export");
      Alert.alert(
        "DPDP Data Export Ready",
        `Exported full records:\n${JSON.stringify(data).slice(0, 180)}...`
      );
    } catch (e: any) {
      Alert.alert("Export Error", e.message || "Failed to export data archive");
    }
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      "Confirm Account Deletion",
      "Under the DPDP Act, all personal identifiers, files, and tokens will be permanently purged. Proceed?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete My Account",
          style: "destructive",
          onPress: async () => {
            try {
              await mobileApiFetch("/profiles/me/delete", { method: "DELETE" });
              SessionStore.clear();
              Alert.alert("Deactivated", "Your account and data have been permanently deleted.");
              router.replace("/(auth)/sign-in");
            } catch (e: any) {
              Alert.alert("Error", e.message || "Failed to delete account");
            }
          },
        },
      ]
    );
  };

  const handleLogout = () => {
    Alert.alert("Log Out", "Are you sure you want to log out of HeatLedger?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log Out",
        style: "destructive",
        onPress: () => {
          SessionStore.clear();
          router.replace("/(auth)/sign-in");
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Privacy & Settings</Text>
        <Text style={styles.subtitle}>
          You own your data. Manage purpose-specific permissions under Indian DPDP law.
        </Text>

        {/* Language Selection */}
        <View style={styles.card}>
          <Text style={styles.cardHeader}>Language / భాష / भाषा</Text>
          <View style={styles.langRow}>
            {[
              { code: "te", label: "తెలుగు (Telugu)" },
              { code: "hi", label: "हिन्दी (Hindi)" },
              { code: "en", label: "English" },
            ].map((item) => (
              <TouchableOpacity
                key={item.code}
                style={[
                  styles.langOption,
                  selectedLang === item.code && styles.langOptionActive,
                ]}
                onPress={() => setSelectedLang(item.code)}
              >
                <Text
                  style={[
                    styles.langOptionText,
                    selectedLang === item.code && styles.langOptionTextActive,
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Purpose-specific Consent Management */}
        <View style={styles.card}>
          <Text style={styles.cardHeader}>Purpose-Specific Consents</Text>

          <View style={styles.consentRow}>
            <View style={styles.consentInfo}>
              <Text style={styles.consentTitle}>Shift Location Recording</Text>
              <Text style={styles.consentDesc}>
                Collect coarse/fine GPS exclusively while a shift is explicitly active.
              </Text>
            </View>
            <Switch
              value={locationConsent}
              onValueChange={handleToggleLocation}
              trackColor={{ false: "#cbd5e1", true: "#38bdf8" }}
              thumbColor={locationConsent ? "#0284c7" : "#f1f5f9"}
            />
          </View>

          <View style={styles.consentRow}>
            <View style={styles.consentInfo}>
              <Text style={styles.consentTitle}>Earnings Document OCR & Extraction</Text>
              <Text style={styles.consentDesc}>
                Parse uploaded platform slips to extract base pay and deductions.
              </Text>
            </View>
            <Switch
              value={earningsConsent}
              onValueChange={handleToggleEarnings}
              trackColor={{ false: "#cbd5e1", true: "#38bdf8" }}
              thumbColor={earningsConsent ? "#0284c7" : "#f1f5f9"}
            />
          </View>

          <View style={styles.consentRow}>
            <View style={styles.consentInfo}>
              <Text style={styles.consentTitle}>Anonymized Climate Research</Text>
              <Text style={styles.consentDesc}>
                Include aggregated heat exposure in regional union policy reports (k ≥ 5).
              </Text>
            </View>
            <Switch
              value={researchConsent}
              onValueChange={handleToggleResearch}
              trackColor={{ false: "#cbd5e1", true: "#38bdf8" }}
              thumbColor={researchConsent ? "#0284c7" : "#f1f5f9"}
            />
          </View>
        </View>

        {/* Data Rights & Export */}
        <View style={styles.card}>
          <Text style={styles.cardHeader}>Your Data Rights & Session</Text>

          <TouchableOpacity style={styles.actionRow} onPress={handleExportData}>
            <Text style={styles.actionRowText}>📦 Export My Complete Data Portfolio (JSON)</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionRow}
            onPress={handleLogout}
          >
            <Text style={styles.logoutText}>🚪 Log Out of Session</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionRow, styles.deleteRow]}
            onPress={handleDeleteAccount}
          >
            <Text style={styles.deleteText}>🗑️ Delete Account & Purge Data</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.footerNote}>
          HeatLedger Client v1.0.0 • Hyderabad Pilot • Server: /api/v1/
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f8fafc" },
  container: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: "900", color: "#0f172a" },
  subtitle: { fontSize: 13, color: "#64748b", marginTop: 4, marginBottom: 16 },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginBottom: 16,
  },
  cardHeader: { fontSize: 14, fontWeight: "800", color: "#0f172a", marginBottom: 14 },
  langRow: { gap: 8 },
  langOption: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  langOptionActive: { backgroundColor: "#f0f9ff", borderColor: "#0284c7" },
  langOptionText: { fontSize: 13, fontWeight: "600", color: "#475569" },
  langOptionTextActive: { color: "#0284c7", fontWeight: "700" },
  consentRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f1f5f9",
  },
  consentInfo: { flex: 1, paddingRight: 12 },
  consentTitle: { fontSize: 13, fontWeight: "700", color: "#0f172a" },
  consentDesc: { fontSize: 11, color: "#64748b", marginTop: 2 },
  actionRow: {
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#f1f5f9",
  },
  actionRowText: { fontSize: 13, fontWeight: "700", color: "#0284c7" },
  logoutText: { fontSize: 13, fontWeight: "700", color: "#d97706" },
  deleteRow: { borderBottomWidth: 0 },
  deleteText: { fontSize: 13, fontWeight: "700", color: "#dc2626" },
  footerNote: { textAlign: "center", fontSize: 11, color: "#94a3b8", marginTop: 12 },
});
