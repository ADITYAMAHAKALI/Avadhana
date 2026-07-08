interface ClockRingProps {
  size: number;
  strokeWidth: number;
  progress: number; // 0..1
  centerText: string;
  subText?: string;
}

/** SVG progress ring used for the 90-day commitment clock, sized/labeled per call site. */
export function ClockRing({ size, strokeWidth, progress, centerText, subText }: ClockRingProps) {
  const r = (size - strokeWidth) / 2;
  const c = size / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.min(1, Math.max(0, progress));
  const dashOffset = circumference * (1 - clamped);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={c} cy={c} r={r} fill="none" stroke="#EFE7D8" strokeWidth={strokeWidth} />
      <circle
        cx={c}
        cy={c}
        r={r}
        fill="none"
        stroke="var(--color-saffron)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${c} ${c})`}
      />
      <text
        x={c}
        y={subText ? c - 4 : c + 5}
        textAnchor="middle"
        style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: size * 0.24, fill: 'var(--color-ink)' }}
      >
        {centerText}
      </text>
      {subText && (
        <text
          x={c}
          y={c + size * 0.16}
          textAnchor="middle"
          style={{ fontFamily: 'var(--font-mono)', fontSize: size * 0.08, fill: 'var(--color-ink-80)', letterSpacing: '0.06em' }}
        >
          {subText}
        </text>
      )}
    </svg>
  );
}
