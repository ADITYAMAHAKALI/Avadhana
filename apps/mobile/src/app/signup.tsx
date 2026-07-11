import { useState } from 'react';
import { Link, router } from 'expo-router';
import { ActivityIndicator, Pressable, StyleSheet, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useAuth } from '@/context/AuthContext';
import { Spacing } from '@/constants/theme';

export default function SignupScreen() {
  const { signup, isAuthenticating, authError, clearAuthError } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [location, setLocation] = useState('');

  async function handleSubmit() {
    try {
      await signup({ name, email, password, location });
      router.replace('/(tabs)');
    } catch {
      // authError is already set by AuthContext; nothing else to do here.
    }
  }

  function withClearedError(setter: (text: string) => void) {
    return (text: string) => {
      setter(text);
      clearAuthError();
    };
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ThemedText type="title" style={styles.title}>
          Avadhana
        </ThemedText>
        <ThemedText type="subtitle" style={styles.subtitle}>
          Create an account
        </ThemedText>

        <TextInput style={styles.input} placeholder="Name" value={name} onChangeText={withClearedError(setName)} />
        <TextInput
          style={styles.input}
          placeholder="Email"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={withClearedError(setEmail)}
        />
        <TextInput style={styles.input} placeholder="Password" secureTextEntry value={password} onChangeText={withClearedError(setPassword)} />
        <TextInput style={styles.input} placeholder="Location" value={location} onChangeText={withClearedError(setLocation)} />

        {authError && (
          <ThemedText type="small" themeColor="text" style={styles.error}>
            {authError}
          </ThemedText>
        )}

        <Pressable
          style={[styles.button, isAuthenticating && styles.buttonDisabled]}
          disabled={isAuthenticating || !name || !email || !password || !location}
          onPress={handleSubmit}>
          {isAuthenticating ? <ActivityIndicator color="#ffffff" /> : <ThemedText style={styles.buttonLabel}>Sign up</ThemedText>}
        </Pressable>

        <Link href="/login" style={styles.link}>
          <ThemedText type="link">Already have an account? Log in</ThemedText>
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
