export interface Product {
  id: number;
  asin: string | null;
  title: string;
  category: string;
  price: string | null;
  rating: number | null;
  reviews_count: number;
  product_url: string;
  image_url: string;
  keyword: string | null;
  boost_score: number;
  trend_score: number;
  trend_change_percent: number | null;
  score: number | null;
  reasoning: string | null;
  score_source: string | null;
  scoring_provider: string | null;
  updated_at: string;
  last_scraped_at: string | null;
  last_trend_collected_at: string | null;
  last_scored_at: string | null;
}

export interface ProductList {
  items: Product[];
  total: number;
}

export interface TaskAccepted {
  task_id: string;
  status: string;
}

export interface TaskState extends TaskAccepted {
  result?: Record<string, unknown> | null;
}

export interface SalesBoostProduct {
  id: number;
  title: string;
  category: string;
  keywords: string[];
  created_at: string;
  rescore_task_id?: string | null;
}

export interface CSVImportResult {
  created: number;
  duplicates: number;
  invalid_rows: Array<{ row: number; error: string }>;
  rescore_task_id: string | null;
}
