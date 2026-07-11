import { useCallback, useEffect, useState } from 'react';
import { router } from 'expo-router';
import { ActivityIndicator, FlatList, Pressable, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { currentUserApi } from '@/data/real/currentUserApi';
import { problemsApi } from '@/data/real/problemsApi';
import type { CommittedProblemSummary, Problem } from '@/data/types/domain';

interface CommittedCard {
  summary: CommittedProblemSummary;
  problem: Problem;
}

/** A checkpoint is due once dayInCycle reaches the 90-day minimum. The backend re-validates on submit regardless. */
function isCheckpointDue(summary: CommittedProblemSummary): boolean {
  return summary.dayInCycle >= summary.cycleLengthDays;
}

export default function DashboardScreen() {
  const [cards, setCards] = useState<CommittedCard[]>([]);
  const [slots, setSlots] = useState({ used: 0, total: 3 });
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    const [committed, slotCount] = await Promise.all([
      currentUserApi.getCommittedProblems(),
      currentUserApi.getFocusSlotCount(),
    ]);
    const joined = await Promise.all(
      committed.map(async (summary) => {
        const problem = await problemsApi.getById(summary.problemId);
        return problem ? { summary, problem } : null;
      }),
    );
    setCards(joined.filter((c): c is CommittedCard => c !== null));
    setSlots(slotCount);
    setLoaded(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const openSlots = Math.max(0, slots.total - slots.used);
  const problemCountLabel = cards.length === 0 ? 'No problems committed yet.' : `${cards.length} problem${cards.length === 1 ? '' : 's'} committed.`;

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
        <ThemedText type="title" style={styles.title}>
          Your focus
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          {problemCountLabel} Everything you owe is here — nothing else.
        </ThemedText>

        <FlatList
          data={cards}
          keyExtractor={(item) => item.problem.id}
          contentContainerStyle={styles.list}
          ListFooterComponent={
            openSlots > 0 ? (
              <Pressable style={styles.openSlotCard} onPress={() => router.push('/(tabs)/discover')}>
                <ThemedText type="smallBold">+ One slot open</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  Choose deliberately. You can&apos;t free it again for 90 days.
                </ThemedText>
              </Pressable>
            ) : null
          }
          renderItem={({ item }) => {
            const due = isCheckpointDue(item.summary);
            return (
              <Pressable
                style={styles.card}
                onPress={() => router.push({ pathname: '/problems/[problemId]', params: { problemId: item.problem.id } })}>
                <ThemedText type="smallBold">{item.problem.tier}-tier</ThemedText>
                <ThemedText type="default" style={styles.cardTitle}>
                  {item.problem.title}
                </ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {item.problem.location} · Day {item.summary.dayInCycle} / {item.summary.cycleLengthDays}
                </ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  You · {item.summary.role}
                </ThemedText>
                {due && (
                  <ThemedView type="backgroundSelected" style={styles.dueBadge}>
                    <ThemedText type="small">Checkpoint due</ThemedText>
                  </ThemedView>
                )}
                <ThemedText type="small" themeColor="textSecondary" style={styles.nextTaskLabel}>
                  NEXT TASK · YOURS
                </ThemedText>
                <ThemedText type="small">{item.summary.nextTask ?? 'No task assigned yet'}</ThemedText>
              </Pressable>
            );
          }}
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
  title: {
    marginTop: Spacing.two,
  },
  list: {
    gap: Spacing.three,
    paddingVertical: Spacing.three,
  },
  card: {
    borderWidth: 1,
    borderColor: '#D0D3D9',
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.half,
  },
  cardTitle: {
    fontWeight: '600',
  },
  dueBadge: {
    alignSelf: 'flex-start',
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
    marginTop: Spacing.one,
  },
  nextTaskLabel: {
    marginTop: Spacing.two,
  },
  openSlotCard: {
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: '#D0D3D9',
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.one,
    alignItems: 'center',
  },
});
