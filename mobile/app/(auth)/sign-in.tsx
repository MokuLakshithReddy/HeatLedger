import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { mobileApiFetch } from "@/lib/api";
import { SessionStore } from "@/lib/store";

export default function SignInScreen() {
  const [emailOrPhone, setEmailOrPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    if (!emailOrPhone.trim() || !password) {
      Alert.alert("Missing Fields", "Please enter your email or phone number and password.");
      return;
    }

    setLoading(true);
    try {
      const isEmail = emailOrPhone.includes("@");
      const body = isEmail ? { email: emailOrPhone.trim(), password } : { phone: emailOrPhone.trim(), password };
      
      const authData = await mobileApiFetch<any>("/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      });

      // Save verified authenticated session
      SessionStore.set({
        token: authData.access_token,
        userId: authData.user_id,
        fullName: authData.user_id,
        role: authData.role,
        language: authData.preferred_language || "en",
      });

      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert("Authentication Failed", e.message || "Invalid credentials. Please verify your details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.brandTitle}>HeatLedger</Text>
          <Text style={styles.tagline}>Your work. Your conditions. Your evidence.</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.formTitle}>Worker Sign In</Text>

          <Text style={styles.label}>Email or Phone Number</Text>
          <TextInput
            style={styles.input}
            value={emailOrPhone}
            onChangeText={setEmailOrPhone}
            placeholder="e.g. worker@example.com or +91 9876543210"
            autoCapitalize="none"
            editable={!loading}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
            editable={!loading}
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSignIn}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.buttonText}>Sign In to HeatLedger</Text>
            )}
          </TouchableOpacity>

          <View style={styles.footerLinkContainer}>
            <Text style={styles.footerText}>New to HeatLedger? </Text>
            <TouchableOpacity onPress={() => router.push("/(auth)/sign-up")}>
              <Text style={styles.linkText}>Register Account</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#0f172a" },
  container: { flex: 1, padding: 24, justifyContent: "center" },
  header: { marginBottom: 32, alignItems: "center" },
  brandTitle: { fontSize: 32, fontWeight: "800", color: "#f97316", letterSpacing: 0.5 },
  tagline: { fontSize: 14, color: "#94a3b8", marginTop: 6, textAlign: "center" },
  formCard: { backgroundColor: "#1e293b", padding: 24, borderRadius: 16, borderWidth: 1, borderColor: "#334155" },
  formTitle: { fontSize: 20, fontWeight: "700", color: "#f8fafc", marginBottom: 20 },
  label: { fontSize: 13, fontWeight: "600", color: "#cbd5e1", marginBottom: 6 },
  input: {
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 8,
    padding: 12,
    color: "#f8fafc",
    fontSize: 15,
    marginBottom: 16,
  },
  button: {
    backgroundColor: "#f97316",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#ffffff", fontSize: 16, fontWeight: "700" },
  footerLinkContainer: { flexDirection: "row", justifyContent: "center", marginTop: 20 },
  footerText: { color: "#94a3b8", fontSize: 14 },
  linkText: { color: "#38bdf8", fontSize: 14, fontWeight: "600" },
});
