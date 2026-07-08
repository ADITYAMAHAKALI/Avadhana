import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { problemsPort } from '../data';
import type { Problem, ProblemGraphEdge, ProblemGraphNode } from '../types/domain';
import { PageHeader } from '../components/shared/PageHeader';
import { TierChip } from '../components/shared/TierChip';
import styles from './GraphPage.module.css';

// Node cards are ~200px wide; approximate their visual center for line endpoints
// since nodes render as absolutely-positioned HTML cards overlaid on the SVG,
// not SVG shapes themselves.
const NODE_CONNECT_OFFSET_X = 80;
const NODE_CONNECT_OFFSET_Y = 30;

export function GraphPage() {
  const { problemId } = useParams<{ problemId: string }>();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [nodes, setNodes] = useState<ProblemGraphNode[]>([]);
  const [edges, setEdges] = useState<ProblemGraphEdge[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!problemId) return;
    let cancelled = false;

    async function load() {
      const [problemDetail, graph] = await Promise.all([
        problemsPort.getById(problemId!),
        problemsPort.getGraph(problemId!),
      ]);
      if (!cancelled) {
        setProblem(problemDetail);
        setNodes(graph.nodes);
        setEdges(graph.edges);
        setLoaded(true);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [problemId]);

  const nodesById = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={problem?.parentProblemTitle ?? problem?.title ?? 'Problem lineage'}
        title="Problem graph"
        subtitle="Problems split into sub-problems as scope narrows, and merge back when overlap is recognized — tracked like branches, never deleted."
      />

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={styles.legendLineSplit} />
          Split (parent → child)
        </span>
        <span className={styles.legendItem}>
          <span className={styles.legendLineMerge} />
          Merge
        </span>
      </div>

      <div className={styles.canvas}>
        {loaded && (
          <>
            <svg width="100%" height="100%" viewBox="0 0 900 480" className={styles.svg}>
              {edges.map((edge, i) => {
                const from = nodesById.get(edge.fromId);
                const to = nodesById.get(edge.toId);
                if (!from || !to) return null;
                const x1 = from.x + NODE_CONNECT_OFFSET_X;
                const y1 = from.y + NODE_CONNECT_OFFSET_Y;
                const x2 = to.x + NODE_CONNECT_OFFSET_X;
                const y2 = to.y + NODE_CONNECT_OFFSET_Y;
                return (
                  <line
                    key={`${edge.fromId}-${edge.toId}-${i}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    className={edge.kind === 'merge' ? styles.edgeMerge : styles.edgeSplit}
                  />
                );
              })}
            </svg>

            {nodes.map((node) => (
              <div
                key={node.id}
                className={styles.nodeWrap}
                style={{ left: node.x, top: node.y }}
              >
                {node.isMerge ? (
                  <span className={styles.mergeBadge}>merge</span>
                ) : (
                  <TierChip tier={node.tier} />
                )}
                <div
                  className={`${styles.nodeCard} ${node.highlighted ? styles.nodeHighlighted : ''} ${
                    node.isMerge ? styles.nodeMerge : ''
                  }`}
                >
                  <div className={styles.nodeTitle}>{node.title}</div>
                  <div className={`${styles.nodeNote} ${node.highlighted ? styles.nodeNoteHighlighted : ''} ${
                    node.isMerge ? styles.nodeNoteMerge : ''
                  }`}>
                    {node.note}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
