import { useEffect, useState } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, FlatList, StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { problemsApi } from '@/data/real/problemsApi';
import type { FeedPost, Problem } from '@/data/types/domain';

export default function ProblemDetailScreen() {
  const { problemId } = useLocalSearchParams<{ problemId: string }>();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [feed, setFeed] = useState<FeedPost[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([problemsApi.getById(problemId), problemsApi.getFeed(problemId)])
      .then(([foundProblem, posts]) => {
        if (cancelled) return;
        setProblem(foundProblem);
        setFeed(posts);
        setLoaded(true);
      })
      .catch(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [problemId]);

  if (!loaded) {
    return (
      <ThemedView style={styles.loadingContainer}>
        <ActivityIndicator />
      </ThemedView>
    );
  }

  if (!problem) {
    return (
      <ThemedView style={styles.loadingContainer}>
        <ThemedText themeColor="textSecondary">Problem not found.</ThemedText>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <FlatList
        data={feed}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <ThemedView style={styles.header}>
            <ThemedText type="smallBold">
              {problem.tier}-tier · {problem.category}
            </ThemedText>
            <ThemedText type="title" style={styles.title}>
              {problem.title}
            </ThemedText>
            <ThemedText themeColor="textSecondary">{problem.summary}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {problem.location} · {problem.thinkerCount} thinkers · {problem.actorCount} actors · {problem.backerCount} backers
            </ThemedText>

            {/* Commit modal ships in #90 — reads and shares are open to anyone; posting,
                commenting, and liking need a spent focus slot per CLAUDE.md's
                commitment-gated-voice principle, so this is explained rather than
                silently hidden. */}
            <ThemedView type="backgroundElement" style={styles.gateNotice}>
              <ThemedText type="small">
                You can read and share this problem&apos;s progress. Posting, commenting, and voting require committing a focus slot.
              </ThemedText>
            </ThemedView>

            <ThemedText type="smallBold" style={styles.feedLabel}>
              Feed
            </ThemedText>
          </ThemedView>
        }
        ListEmptyComponent={
          <ThemedText themeColor="textSecondary" style={styles.emptyFeed}>
            No posts yet.
          </ThemedText>
        }
        renderItem={({ item }) => (
          <ThemedView style={styles.post}>
            <ThemedView style={styles.postHeader}>
              <ThemedView style={[styles.avatar, { backgroundColor: item.authorColor }]}>
                <ThemedText type="small" style={styles.avatarText}>
                  {item.authorInitials}
                </ThemedText>
              </ThemedView>
              <ThemedView style={styles.postMeta}>
                <ThemedText type="smallBold">{item.authorName}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {item.roleLabel} · {item.timeAgo}
                </ThemedText>
              </ThemedView>
            </ThemedView>
            <ThemedText>{item.body}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              {item.likeCount} likes
            </ThemedText>
          </ThemedView>
        )}
      />
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
  list: {
    paddingHorizontal: Spacing.three,
    paddingBottom: Spacing.five,
  },
  header: {
    gap: Spacing.two,
    paddingVertical: Spacing.three,
  },
  title: {
    fontSize: 28,
    lineHeight: 34,
  },
  gateNotice: {
    borderRadius: Spacing.two,
    padding: Spacing.three,
    marginTop: Spacing.two,
  },
  feedLabel: {
    marginTop: Spacing.two,
  },
  emptyFeed: {
    paddingVertical: Spacing.three,
  },
  post: {
    borderWidth: 1,
    borderColor: '#D0D3D9',
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
    marginBottom: Spacing.three,
  },
  postHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#ffffff',
  },
  postMeta: {
    gap: 0,
  },
});
