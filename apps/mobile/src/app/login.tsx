import { useState } from 'react';
import { Link, router } from 'expo-router';
import { ActivityIndicator, Pressable, StyleSheet, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useAuth } from '@/context/AuthContext';
import { Spacing } from '@/constants/theme';

export default function LoginScreen() {
  const { login, isAuthenticating, authError, clearAuthError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  async function handleSubmit() {
    try {
      await login({ email, password });
      router.replace('/(tabs)');
    } catch {
      // authError is already set by AuthContext; nothing else to do here.
    }
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ThemedText type="title" style={styles.title}>
          Avadhana
        </ThemedText>
        <ThemedText type="subtitle" style={styles.subtitle}>
          Log in
        </ThemedText>

        <TextInput
          style={styles.input}
          placeholder="Email"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={(text) => {
            setEmail(text);
            clearAuthError();
          }}
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={(text) => {
            setPassword(text);
            clearAuthError();
          }}
        />

        {authError && (
          <ThemedText type="small" themeColor="text" style={styles.error}>
            {authError}
          </ThemedText>
        )}

        <Pressable
          style={[styles.button, isAuthenticating && styles.buttonDisabled]}
          disabled={isAuthenticating || !email || !password}
          onPress={handleSubmit}>
          {isAuthenticating ? <ActivityIndicator color="#ffffff" /> : <ThemedText style={styles.buttonLabel}>Log in</ThemedText>}
        </Pressable>

        <Link href="/signup" style={styles.link}>
          <ThemedText type="link">Don&apos;t have an account? Sign up</ThemedText>
        </Link>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: Spacing.four,
    gap: Spacing.three,
  },
  title: {
    textAlign: 'center',
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: Spacing.three,
  },
  input: {
    borderWidth: 1,
    borderColor: '#D0D3D9',
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 16,
  },
  error: {
    color: '#D64545',
  },
  button: {
    backgroundColor: '#208AEF',
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonLabel: {
    color: '#ffffff',
    fontWeight: '600',
  },
  link: {
    alignSelf: 'center',
    marginTop: Spacing.two,
  },
});
