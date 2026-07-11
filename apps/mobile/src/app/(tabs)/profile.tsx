import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { currentUserApi } from '@/data/real/currentUserApi';
import type { CommitmentHistoryEntry, User } from '@/data/types/domain';

const STATUS_LABEL: Record<CommitmentHistoryEntry['status'], string> = {
  active: 'Active',
  resolved: 'Resolved',
  continued: 'Continued',
  abandoned: 'Abandoned',
};

export default function ProfileScreen() {
  const { logout } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [history, setHistory] = useState<CommitmentHistoryEntry[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([currentUserApi.getCurrentUser(), currentUserApi.getCommitmentHistory()])
      .then(([currentUser, commitmentHistory]) => {
        if (cancelled) return;
        setUser(currentUser);
        setHistory(commitmentHistory);
        setLoaded(true);
      })
      .catch(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!loaded) {
    return (
      <ThemedView style={styles.loadingContainer}>
        <ActivityIndicator />
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        {user && (
          <ThemedView style={styles.headerRow}>
            <ThemedView style={[styles.avatar, { backgroundColor: user.avatarColor }]}>
              <ThemedText type="smallBold" style={styles.avatarText}>
                {user.initials}
              </ThemedText>
            </ThemedView>
            <ThemedView style={styles.identity}>
              <ThemedText type="subtitle">{user.name}</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {user.location} · member since {user.memberSince}
              </ThemedText>
            </ThemedView>
            <ThemedView style={styles.reputationBlock}>
              <ThemedText type="title" style={styles.reputationNumber}>
                {user.reputation}
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                Reputation
              </ThemedText>
            </ThemedView>
          </ThemedView>
        )}

        <ThemedText type="smallBold" style={styles.sectionLabel}>
          Commitment history
        </ThemedText>
        <FlatList
          data={history}
          keyExtractor={(item, index) => `${item.problemTitle}-${index}`}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ThemedText themeColor="textSecondary">No commitment history yet.</ThemedText>}
          renderItem={({ item }) => (
            <ThemedView style={styles.historyRow}>
              <ThemedText type="smallBold">{item.problemTitle}</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {STATUS_LABEL[item.status]} · {item.role}
              </ThemedText>
              {item.note ? (
                <ThemedText type="small" themeColor="textSecondary">
                  {item.note}
                </ThemedText>
              ) : null}
            </ThemedView>
          )}
          ListFooterComponent={
            <Pressable style={styles.logoutButton} onPress={logout}>
              <ThemedText type="smallBold">Log out</ThemedText>
            </Pressable>
          }
        />
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.three,
    gap: Spacing.two,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.three,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#ffffff',
  },
  identity: {
    flex: 1,
    gap: Spacing.half,
  },
  reputationBlock: {
    alignItems: 'center',
  },
  reputationNumber: {
    fontSize: 28,
    lineHeight: 32,
  },
  sectionLabel: {
    marginTop: Spacing.two,
  },
  list: {
    gap: Spacing.two,
    paddingBottom: Spacing.five,
  },
  historyRow: {
    borderWidth: 1,
    borderColor: '#D0D3D9',
    borderRadius: Spacing.two,
    padding: Spacing.three,
    gap: Spacing.half,
  },
  logoutButton: {
    marginTop: Spacing.four,
    alignItems: 'center',
    paddingVertical: Spacing.three,
    borderRadius: Spacing.two,
    borderWidth: 1,
    borderColor: '#D0D3D9',
  },
});
