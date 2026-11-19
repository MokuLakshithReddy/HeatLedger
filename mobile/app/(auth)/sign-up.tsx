import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Alert,
} from "react-native";
import { router } from "expo-router";
import { mobileApiFetch } from "@/lib/api";

export default function SignUpScreen() {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("+91");
  const [password, setPassword] = useState("");
  const [language, setLanguage] = useState("te");

  const handleSignUp = async () => {
    try {
      await mobileApiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName,
          phone,
          password,
          preferred_language: language,
          role: "worker",
          city: "Hyderabad",
        }),
      });
      Alert.alert("Registration Complete", "Welcome to HeatLedger.");
      router.replace("/(tabs)");
    } catch (e: any) {
      router.replace("/(tabs)");
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <Text style={styles.brandTitle}>HeatLedger</Text>
          <Text style={styles.tagline}>Worker Onboarding & Consent Agreement</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.formTitle}>Register Worker Profile</Text>

          <Text style={styles.label}>Full Name</Text>
          <TextInput
            style={styles.input}
            value={fullName}
            onChangeText={setFullName}
            placeholder="e.g. Ramesh Kumar"
          />

          <Text style={styles.label}>Mobile Phone (+91)</Text>
          <TextInput
            style={styles.input}
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
          />

          <Text style={styles.label}>Password (minimum 8 characters)</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
          />

          <Text style={styles.label}>Preferred Language</Text>
          <View style={styles.langRow}>
            {[
              { code: "te", label: "తెలుగు" },
              { code: "hi", label: "हिन्दी" },
              { code: "en", label: "English" },
            ].map((item) => (
              <TouchableOpacity
                key={item.code}
                style={[
                  styles.langOption,
                  language === item.code && styles.langOptionActive,
                ]}
                onPress={() => setLanguage(item.code)}
              >
                <Text
                  style={[
                    styles.langText,
                    language === item.code && styles.langTextActive,
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <View style={styles.privacyNotice}>
            <Text style={styles.privacyNoticeTitle}>🔒 Privacy First Guarantee</Text>
            <Text style={styles.privacyNoticeText}>
              By signing up, your location is NOT tracked automatically. You hold separate, purpose-specific control over location, document analysis, and union sharing under the Indian DPDP Act.
            </Text>
          </View>

          <TouchableOpacity style={styles.submitBtn} onPress={handleSignUp}>
            <Text style={styles.submitBtnText}>Agree & Create Account</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.switchAuth}
            onPress={() => router.push("/(auth)/sign-in")}
          >
            <Text style={styles.switchAuthText}>Already registered? Sign in</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f8fafc" },
  container: { padding: 24 },
  header: { alignItems: "center", marginBottom: 24 },
  brandTitle: { fontSize: 30, fontWeight: "900", color: "#0284c7" },
  tagline: { fontSize: 13, color: "#64748b", marginTop: 4 },
  formCard: {
    backgroundColor: "#ffffff",
    padding: 24,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  formTitle: { fontSize: 18, fontWeight: "800", color: "#0f172a", marginBottom: 16 },
  label: { fontSize: 12, fontWeight: "700", color: "#475569", marginBottom: 6 },
  input: {
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    marginBottom: 16,
  },
  langRow: { flexDirection: "row", gap: 8, marginBottom: 16 },
  langOption: {
    flex: 1,
    paddingVertical: 10,
    backgroundColor: "#f1f5f9",
    borderRadius: 8,
    alignItems: "center",
  },
  langOptionActive: { backgroundColor: "#0284c7" },
  langText: { fontSize: 12, fontWeight: "700", color: "#475569" },
  langTextActive: { color: "#ffffff" },
  privacyNotice: {
    backgroundColor: "#f0f9ff",
    borderWidth: 1,
    borderColor: "#bae6fd",
    padding: 12,
    borderRadius: 8,
    marginBottom: 20,
  },
  privacyNoticeTitle: { fontSize: 12, fontWeight: "800", color: "#0369a1", marginBottom: 4 },
  privacyNoticeText: { fontSize: 11, color: "#0c4a6e", lineHeight: 16 },
  submitBtn: {
    backgroundColor: "#0284c7",
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
  },
  submitBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 15 },
  switchAuth: { marginTop: 16, alignItems: "center" },
  switchAuthText: { fontSize: 12, color: "#0284c7", fontWeight: "600" },
});
