export function ScoreBadge({ score }: { score: number | null }) {
  const tone = score === null ? "muted" : score >= 75 ? "high" : score >= 50 ? "medium" : "low";
  return (
    <span className={`score score-${tone}`} aria-label={score === null ? "Not scored" : `Score ${score}`}>
      {score ?? "—"}
    </span>
  );
}
