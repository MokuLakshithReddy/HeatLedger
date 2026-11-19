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
  ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { mobileApiFetch } from "@/lib/api";
import { SessionStore } from "@/lib/store";

export default function SignUpScreen() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("+91");
  const [password, setPassword] = useState("");
  const [language, setLanguage] = useState<"en" | "te" | "hi">("te");
  const [loading, setLoading] = useState(false);

  const handleSignUp = async () => {
    if (!password || password.length < 8) {
      Alert.alert("Invalid Password", "Password must be at least 8 characters long.");
      return;
    }
    if (!email && (!phone || phone.length < 10)) {
      Alert.alert("Missing Contact", "Please provide a valid email or phone number.");
      return;
    }

    setLoading(true);
    try {
      const regData = await mobileApiFetch<any>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName.trim() || undefined,
          email: email.trim() || undefined,
          phone: phone.trim() || undefined,
          password,
          preferred_language: language,
          role: "worker",
          city: "Hyderabad",
        }),
      });

      // Save authenticated session
      SessionStore.set({
        token: regData.access_token,
        userId: regData.user_id,
        fullName: fullName || "Worker",
        role: regData.role,
        language: language,
      });

      Alert.alert("Registration Complete", "Welcome to HeatLedger. Your worker account is now active.");
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert("Registration Failed", e.message || "Could not register account. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <Text style={styles.brandTitle}>HeatLedger</Text>
          <Text style={styles.tagline}>Worker Onboarding & Evidence Platform</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.formTitle}>Register Worker Profile</Text>

          <Text style={styles.label}>Full Name</Text>
          <TextInput
            style={styles.input}
            value={fullName}
            onChangeText={setFullName}
            placeholder="e.g. Ramesh Kumar"
            editable={!loading}
          />

          <Text style={styles.label}>Email Address (Optional)</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="e.g. ramesh@example.com"
            autoCapitalize="none"
            editable={!loading}
          />

          <Text style={styles.label}>Mobile Phone (+91)</Text>
          <TextInput
            style={styles.input}
            value={phone}
            onChangeText={setPhone}
            placeholder="+91 9876543210"
            keyboardType="phone-pad"
            editable={!loading}
          />

          <Text style={styles.label}>Password (min 8 chars)</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
            editable={!loading}
          />

          <Text style={styles.label}>Preferred Language</Text>
          <View style={styles.langRow}>
            {(["en", "te", "hi"] as const).map((l) => (
              <TouchableOpacity
                key={l}
                style={[styles.langButton, language === l && styles.langButtonActive]}
                onPress={() => setLanguage(l)}
                disabled={loading}
              >
                <Text style={[styles.langText, language === l && styles.langTextActive]}>
                  {l === "te" ? "తెలుగు" : l === "hi" ? "हिन्दी" : "English"}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSignUp}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.buttonText}>Complete Registration</Text>
            )}
          </TouchableOpacity>

          <View style={styles.footerLinkContainer}>
            <Text style={styles.footerText}>Already registered? </Text>
            <TouchableOpacity onPress={() => router.push("/(auth)/sign-in")}>
              <Text style={styles.linkText}>Sign In</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#0f172a" },
  container: { padding: 24, justifyContent: "center" },
  header: { marginBottom: 24, alignItems: "center" },
  brandTitle: { fontSize: 30, fontWeight: "800", color: "#f97316" },
  tagline: { fontSize: 13, color: "#94a3b8", marginTop: 4, textAlign: "center" },
  formCard: { backgroundColor: "#1e293b", padding: 20, borderRadius: 16, borderWidth: 1, borderColor: "#334155" },
  formTitle: { fontSize: 18, fontWeight: "700", color: "#f8fafc", marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "600", color: "#cbd5e1", marginBottom: 6 },
  input: {
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 8,
    padding: 10,
    color: "#f8fafc",
    fontSize: 14,
    marginBottom: 14,
  },
  langRow: { flexDirection: "row", gap: 8, marginBottom: 16 },
  langButton: { flex: 1, padding: 10, borderRadius: 8, borderWidth: 1, borderColor: "#334155", alignItems: "center" },
  langButtonActive: { backgroundColor: "#f97316", borderColor: "#f97316" },
  langText: { color: "#94a3b8", fontSize: 13, fontWeight: "600" },
  langTextActive: { color: "#ffffff", fontWeight: "700" },
  button: { backgroundColor: "#f97316", padding: 14, borderRadius: 8, alignItems: "center", marginTop: 8 },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#ffffff", fontSize: 15, fontWeight: "700" },
  footerLinkContainer: { flexDirection: "row", justifyContent: "center", marginTop: 18 },
  footerText: { color: "#94a3b8", fontSize: 13 },
  linkText: { color: "#38bdf8", fontSize: 13, fontWeight: "600" },
});
