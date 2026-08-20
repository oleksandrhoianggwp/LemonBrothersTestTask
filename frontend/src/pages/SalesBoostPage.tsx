import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import { Layout } from "../components/Layout";
import type { SalesBoostProduct } from "../types";

export function SalesBoostPage() {
  const [items, setItems] = useState<SalesBoostProduct[]>([]);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [keywords, setKeywords] = useState("");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try { setItems(await api.salesBoost()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load history"); } finally { setLoading(false); }
  }, []);
  useEffect(() => void load(), [load]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setFeedback("");
    try {
      await api.addSalesBoost({ title, category, keywords: keywords.split(",").map((item) => item.trim()).filter(Boolean) });
      setTitle(""); setCategory(""); setKeywords(""); setFeedback("Historical product added; rescoring was queued."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to add product"); }
  }

  async function upload(file: File | undefined) {
    if (!file) return; setError(""); setFeedback("");
    try {
      const result = await api.importSalesBoost(file);
      setFeedback(result.created === 0 && result.duplicates > 0
        ? `No new products were added; all ${result.duplicates} CSV rows already exist.`
        : `Imported ${result.created}; skipped ${result.duplicates} duplicates and ${result.invalid_rows.length} invalid rows.`);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to import CSV"); }
  }

  return (
    <Layout>
      <section className="page-heading"><div><span className="eyebrow">Internal signal</span><h1>Sales Boost history</h1><p>Teach the scoring engine which categories and product themes have already worked.</p></div></section>
      {error && <div className="alert alert-error">{error}</div>}{feedback && <div className="alert alert-success">{feedback}</div>}
      <div className="boost-grid">
        <section className="data-panel form-panel"><div className="panel-heading"><div><h2>Add successful product</h2><p>Keyword and category overlap can contribute up to 20 points.</p></div></div>
          <form className="stack-form" onSubmit={submit}><label>Product title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Enter a product title" required /></label><label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Enter a category" required /></label><label>Keywords<input value={keywords} onChange={(event) => setKeywords(event.target.value)} placeholder="e.g. cooling, portable fan, summer" /><small>Separate keywords with commas.</small></label><button className="button button-primary">Add product</button></form>
          <div className="upload-zone"><div><strong>Bulk import CSV</strong><span>Columns: title, category, keywords · max 2 MB</span></div><label className="button button-secondary">Choose CSV<input type="file" accept=".csv,text/csv" onChange={(event) => void upload(event.target.files?.[0])} /></label></div>
        </section>
        <section className="data-panel"><div className="panel-heading"><div><h2>Successful products</h2><p>{items.length} historical records</p></div></div>
          {loading ? <div className="empty-state">Loading history…</div> : items.length === 0 ? <div className="empty-state"><strong>No history yet</strong><span>Add a product manually or upload a CSV.</span></div> : <div className="history-list">{items.map((item) => <article key={item.id}><div><strong>{item.title}</strong><span>{item.category}</span></div><div className="tags">{item.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}</div></article>)}</div>}
        </section>
      </div>
    </Layout>
  );
}
