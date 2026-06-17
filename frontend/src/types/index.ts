export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: "free" | "pro" | "enterprise";
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: "admin" | "user";
  organization: Organization | null;
  date_joined: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  file_size: number;
  row_count: number | null;
  column_count: number | null;
  status: "pending" | "processing" | "ready" | "failed";
  uploaded_by_email: string;
  created_at: string;
}

export interface KPISummary {
  dataset_id: string;
  total: number;
  average: number;
  median: number;
  std_dev: number;
  min_value: number;
  max_value: number;
  growth_rate: number | null;
  computed_at: string;
}

export interface TrendPoint {
  period: string;
  value: number;
  moving_avg: number | null;
}

export interface TrendAnalysis {
  dataset_id: string;
  direction: "up" | "down" | "flat";
  slope: number;
  r_squared: number;
  points: TrendPoint[];
}

export interface AnomalyPoint {
  index: number;
  value: number;
  expected: number;
  z_score: number;
  severity: "low" | "medium" | "high";
}

export interface AnomalyReport {
  dataset_id: string;
  anomaly_count: number;
  anomalies: AnomalyPoint[];
}

export interface InsightItem {
  type: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
  data?: Record<string, unknown>;
}

export interface AnalyticsResponse {
  dataset_id: string;
  org_id: string;
  kpi: KPISummary;
  trends: TrendAnalysis;
  anomalies: AnomalyReport;
  computed_at: string;
}

export interface InsightsResponse {
  dataset_id: string;
  insights: InsightItem[];
  generated_at: string;
}
