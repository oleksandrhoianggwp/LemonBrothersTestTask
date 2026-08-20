import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Layout } from "../components/Layout";
import { ScoreBadge } from "../components/ScoreBadge";
import type { Product, TaskState } from "../types";

const terminalStates = new Set(["SUCCESS", "FAILURE", "REVOKED"]);

export function DashboardPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [task, setTask] = useState<TaskState | null>(null);

  const loadProducts = useCallback(async () => {
    setError("");
    try {
      const response = await api.products();
      setProducts(response.items);
      setTotal(response.total);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load products");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void loadProducts(), [loadProducts]);
  useEffect(() => {
    if (!task || terminalStates.has(task.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await api.task(task.task_id);
        setTask(next);
        if (next.status === "SUCCESS") void loadProducts();
      } catch {
        window.clearInterval(timer);
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [task, loadProducts]);

  async function enqueue(kind: "amazon" | "trends") {
    setError("");
    try {
      const accepted = kind === "amazon" ? await api.runAmazon() : await api.runTrends();
      setTask(accepted);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to enqueue task");
    }
  }

  const scored = products.filter((product) => product.score !== null);
  const average = scored.length ? Math.round(scored.reduce((sum, product) => sum + (product.score ?? 0), 0) / scored.length) : null;
  const taskOutcome = task ? describeTask(task) : null;

  return (
    <Layout>
      <section className="page-heading">
        <div><span className="eyebrow">Opportunity overview</span><h1>Trending products</h1><p>Evidence-backed product candidates ranked by demand, quality, confidence, and historical fit.</p></div>
        <div className="actions">
          <button className="button button-secondary" onClick={() => void enqueue("amazon")} disabled={Boolean(task && !terminalStates.has(task.status))}>Run Amazon collection</button>
          <button className="button button-primary" onClick={() => void enqueue("trends")} disabled={Boolean(task && !terminalStates.has(task.status))}>Run trend collection</button>
          <button className="button button-ghost" onClick={() => void loadProducts()}>Refresh</button>
        </div>
      </section>
      {task && taskOutcome && <div className={`task-banner ${taskOutcome.tone}`}><span className={`status-dot ${terminalStates.has(task.status) ? "complete" : ""}`} /><strong>{taskOutcome.label}</strong><span>{taskOutcome.detail}</span><small>{task.task_id.slice(0, 12)}…</small></div>}
      {error && <div className="alert alert-error">{error}</div>}
      <section className="metrics-grid">
        <article><span>Tracked products</span><strong>{total}</strong><small>Amazon candidates</small></article>
        <article><span>Average score</span><strong>{average ?? "—"}</strong><small>Across scored products</small></article>
        <article><span>High potential</span><strong>{products.filter((product) => (product.score ?? 0) >= 75).length}</strong><small>Score 75 or above</small></article>
      </section>
      <section className="data-panel">
        <div className="panel-heading"><div><h2>Product pipeline</h2><p>Latest persisted collection and scoring results.</p></div></div>
        {loading ? <div className="empty-state">Loading product signals…</div> : products.length === 0 ? <div className="empty-state"><strong>No products yet</strong><span>Run Amazon collection to seed the pipeline.</span></div> : <ProductTable products={products} />}
      </section>
    </Layout>
  );
}

function ProductTable({ products }: { products: Product[] }) {
  return (
    <div className="table-wrap">
      <table className="product-table">
        <thead><tr><th>Product</th><th>Market proof</th><th>Trend</th><th>Boost</th><th>Score</th><th>Reasoning</th></tr></thead>
        <tbody>{products.map((product) => <tr key={product.id}>
          <td><div className="product-cell"><img src={product.image_url} alt="" /><div><a href={product.product_url} target="_blank" rel="noreferrer">{product.title}</a><span>{product.category}</span><small>{product.price ? `$${Number(product.price).toFixed(2)}` : "Price unavailable"}</small></div></div></td>
          <td><strong>{product.rating?.toFixed(1) ?? "—"} ★</strong><span className="cell-note">{product.reviews_count.toLocaleString()} reviews</span></td>
          <td><strong>{Math.round(product.trend_score)}/100</strong><span className={`cell-note ${(product.trend_change_percent ?? 0) >= 0 ? "positive" : "negative"}`}>{product.trend_change_percent === null ? "Direction pending" : `${product.trend_change_percent >= 0 ? "+" : ""}${product.trend_change_percent.toFixed(1)}%`}</span><span className="cell-note">{product.last_trend_collected_at ? `As of ${new Date(product.last_trend_collected_at).toLocaleString()}` : "No saved snapshot"}</span></td>
          <td><strong>{product.boost_score.toFixed(1)}/20</strong><span className="cell-note">Historical fit</span></td>
          <td><ScoreBadge score={product.score} /><span className="cell-note">{product.score_source ?? "Pending"}</span></td>
          <td className="reasoning"><p>{product.reasoning ?? "Scoring has not run yet."}</p><small>{product.last_scored_at ? `Scored ${new Date(product.last_scored_at).toLocaleString()}` : "Not scored"}</small></td>
        </tr>)}</tbody>
      </table>
    </div>
  );
}

function numericResult(task: TaskState, key: string): number | null {
  const value = task.result?.[key];
  return typeof value === "number" ? value : null;
}

function describeTask(task: TaskState): { label: string; detail: string; tone: string } {
  if (!terminalStates.has(task.status)) {
    return { label: `Task ${task.status.toLowerCase()}`, detail: "Celery is processing this request.", tone: "" };
  }
  if (task.status !== "SUCCESS") {
    return { label: "Task failed", detail: "See the worker logs for the safe diagnostic.", tone: "failed" };
  }
  const collected = numericResult(task, "collected");
  const failed = numericResult(task, "failed");
  const rateLimited = numericResult(task, "rate_limited");
  if (collected !== null && failed !== null) {
    const detail = `${collected} trend snapshots collected; ${failed} failed${rateLimited ? ` (${rateLimited} rate-limited)` : ""}.`;
    return failed > 0
      ? { label: collected > 0 ? "Completed with warnings" : "No fresh trend data", detail, tone: "warning" }
      : { label: "Trend collection completed", detail, tone: "success" };
  }
  const scraped = numericResult(task, "scraped");
  if (scraped !== null) {
    return { label: "Amazon collection completed", detail: `${scraped} products parsed and persisted.`, tone: "success" };
  }
  return { label: "Task completed", detail: "The background job finished successfully.", tone: "success" };
}
