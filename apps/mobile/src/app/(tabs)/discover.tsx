import { useCallback, useEffect, useState } from 'react';
import { router } from 'expo-router';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { problemsApi } from '@/data/real/problemsApi';
import type { Problem } from '@/data/types/domain';

const SEARCH_DEBOUNCE_MS = 250;

export default function DiscoverScreen() {
  const [query, setQuery] = useState('');
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async (q: string) => {
    const results = await problemsApi.listDiscoverable(q ? { q } : {});
    setProblems(results);
    setLoaded(true);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      load(query).catch(() => setLoaded(true));
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query, load]);

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ThemedText type="title" style={styles.title}>
          Discover
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          Search by topic, location, or tier. Discovery is deliberate, not a feed.
        </ThemedText>

        <TextInput
          style={styles.searchInput}
          placeholder="Search problems…"
          value={query}
          onChangeText={setQuery}
          autoCapitalize="none"
        />

        {!loaded ? (
          <ThemedView style={styles.loadingContainer}>
            <ActivityIndicator />
          </ThemedView>
        ) : (
          <FlatList
            data={problems}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.list}
            ListEmptyComponent={<ThemedText themeColor="textSecondary">No problems match yet.</ThemedText>}
            renderItem={({ item }) => (
              <Pressable
                style={styles.card}
                onPress={() => router.push({ pathname: '/problems/[problemId]', params: { problemId: item.id } })}>
                <ThemedText type="smallBold">{item.tier}-tier · {item.category}</ThemedText>
                <ThemedText style={styles.cardTitle}>{item.title}</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {item.location}
                </ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {item.thinkerCount} thinkers · {item.actorCount} actors · {item.backerCount} backers
                </ThemedText>
              </Pressable>
            )}
          />
        )}
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
    paddingHorizontal: Spacing.three,
    gap: Spacing.two,
  },
  title: {
    marginTop: Spacing.two,
  },
  searchInput: {
    borderWidth: 1,
    borderColor: '#D0D3D9',
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 16,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
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
});
