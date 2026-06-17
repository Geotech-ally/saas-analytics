import React, { useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,

} from "recharts";
import type { Dataset, InsightItem, TrendPoint } from "../../types";
import { useAnalytics } from "../../hooks/useAnalytics";
import { useDatasets } from "../../hooks/useDatasets";

// ── Helpers ────────────────────────────────────────────────────────────────
const fmt = (n: number, decimals = 2) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: decimals }).format(n);

const severityColor: Record<string, string> = {
  info: "#3b82f6",
  warning: "#f59e0b",
  critical: "#ef4444",
};

// ── Sub-components ─────────────────────────────────────────────────────────
function KPICard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi-card">
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      {sub && <p className="kpi-sub">{sub}</p>}
    </div>
  );
}

function InsightCard({ item }: { item: InsightItem }) {
  const color = severityColor[item.severity] ?? "#6b7280";
  return (
    <div className="insight-card" style={{ borderLeftColor: color }}>
      <span className="insight-type" style={{ color }}>
        {item.type.toUpperCase()}
      </span>
      <p className="insight-title">{item.title}</p>
      <p className="insight-desc">{item.description}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: Dataset["status"] }) {
  const map: Record<string, [string, string]> = {
    ready: ["#10b981", "Ready"],
    pending: ["#f59e0b", "Pending"],
    processing: ["#3b82f6", "Processing"],
    failed: ["#ef4444", "Failed"],
  };
  const [color, label] = map[status] ?? ["#6b7280", status];
  return (
    <span className="status-badge" style={{ background: `${color}22`, color }}>
      {label}
    </span>
  );
}

function TrendChart({ points }: { points: TrendPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={points} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
        <XAxis dataKey="period" tick={{ fill: "#6b7280", fontSize: 11 }} />
        <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} width={48} />
        <Tooltip
          contentStyle={{ background: "#0f1923", border: "1px solid #1e2a3a", borderRadius: 8 }}
          labelStyle={{ color: "#94a3b8" }}
          itemStyle={{ color: "#e2e8f0" }}
        />
        <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} name="Value" />
        <Line
          type="monotone"
          dataKey="moving_avg"
          stroke="#10b981"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          dot={false}
          name="Moving Avg"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function AnomalyChart({ points, anomalyIndices }: { points: TrendPoint[]; anomalyIndices: Set<number> }) {
  const data = points.map((p, i) => ({ ...p, anomaly: anomalyIndices.has(i) ? p.value : null }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
        <XAxis dataKey="period" tick={{ fill: "#6b7280", fontSize: 11 }} />
        <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} width={48} />
        <Tooltip
          contentStyle={{ background: "#0f1923", border: "1px solid #1e2a3a", borderRadius: 8 }}
          itemStyle={{ color: "#e2e8f0" }}
        />
        <Bar dataKey="value" fill="#334155" radius={[3, 3, 0, 0]} name="Value" />
        <Bar dataKey="anomaly" fill="#ef4444" radius={[3, 3, 0, 0]} name="Anomaly" />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Analytics Panel ────────────────────────────────────────────────────────
function AnalyticsPanel({ dataset }: { dataset: Dataset }) {
  const { analytics, insights, kpi, loading, error } = useAnalytics(dataset.id);

  if (loading)
    return (
      <div className="panel-state">
        <div className="spinner" />
        <p>Loading analytics…</p>
      </div>
    );

  if (error)
    return (
      <div className="panel-state panel-error">
        <p>⚠ {error}</p>
      </div>
    );

  if (!analytics || !kpi)
    return (
      <div className="panel-state">
        <p>No analytics available for this dataset yet.</p>
      </div>
    );

  const anomalyIndices = new Set(analytics.anomalies.anomalies.map((a) => a.index));
  const growthSign = (kpi.growth_rate ?? 0) >= 0 ? "+" : "";

  return (
    <div className="analytics-panel">
      {/* KPI Row */}
      <div className="kpi-grid">
        <KPICard label="Total" value={fmt(kpi.total)} />
        <KPICard label="Average" value={fmt(kpi.average)} />
        <KPICard label="Median" value={fmt(kpi.median)} />
        <KPICard label="Std Dev" value={fmt(kpi.std_dev)} />
        <KPICard label="Min" value={fmt(kpi.min_value)} />
        <KPICard label="Max" value={fmt(kpi.max_value)} />
        {kpi.growth_rate !== null && (
          <KPICard
            label="Growth"
            value={`${growthSign}${fmt(kpi.growth_rate, 1)}%`}
            sub="vs previous period"
          />
        )}
        <KPICard
          label="Trend"
          value={analytics.trends.direction.charAt(0).toUpperCase() + analytics.trends.direction.slice(1)}
          sub={`R²=${analytics.trends.r_squared.toFixed(2)}`}
        />
      </div>

      {/* Charts */}
      <div className="charts-grid">
        <div className="chart-card">
          <h3 className="chart-title">Value Over Time</h3>
          <TrendChart points={analytics.trends.points} />
        </div>
        <div className="chart-card">
          <h3 className="chart-title">
            Anomaly Map
            {analytics.anomalies.anomaly_count > 0 && (
              <span className="anomaly-badge">{analytics.anomalies.anomaly_count} found</span>
            )}
          </h3>
          <AnomalyChart points={analytics.trends.points} anomalyIndices={anomalyIndices} />
        </div>
      </div>

      {/* Insights */}
      {insights && insights.insights.length > 0 && (
        <div className="insights-section">
          <h3 className="section-title">Insights</h3>
          <div className="insights-grid">
            {insights.insights.map((item, i) => (
              <InsightCard key={i} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Upload Modal ───────────────────────────────────────────────────────────
function UploadModal({ onClose, onUpload }: { onClose: () => void; onUpload: (f: File, n: string, d: string) => Promise<unknown> }) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !name.trim()) { setErr("File and name are required."); return; }
    setUploading(true);
    try {
      await onUpload(file, name.trim(), desc.trim());
      onClose();
    } catch {
      setErr("Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Dataset</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form className="modal-form" onSubmit={handleSubmit}>
          <label>Dataset Name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Q1 Sales Data" /></label>
          <label>Description<input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Optional description" /></label>
          <label>
            File (CSV, Excel, JSON)
            <div
              className="file-drop"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
            >
              {file ? (
                <span className="file-name">📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
              ) : (
                <span className="file-hint">Drag & drop or <label className="file-link">browse<input type="file" hidden accept=".csv,.json,.xlsx,.xls" onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }} /></label></span>
              )}
            </div>
          </label>
          {err && <p className="form-error">{err}</p>}
          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={uploading}>{uploading ? "Uploading…" : "Upload"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────
export default function Dashboard({ userEmail, onLogout }: { userEmail: string; onLogout: () => void }) {
  const { datasets, loading, error, upload, remove, refetch } = useDatasets();
  const [selected, setSelected] = useState<Dataset | null>(null);
  const [showUpload, setShowUpload] = useState(false);



  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">DataLens</span>
        </div>
        <nav className="sidebar-nav">
          <p className="nav-label">Datasets</p>
          {loading && <p className="nav-loading">Loading…</p>}
          {error && <p className="nav-error">{error}</p>}
          {datasets.map((d) => (
            <button
              key={d.id}
              className={`nav-item ${selected?.id === d.id ? "nav-item--active" : ""}`}
              onClick={() => setSelected(d)}
            >
              <span className="nav-item-name">{d.name}</span>
              <StatusBadge status={d.status} />
            </button>
          ))}
          {datasets.length === 0 && !loading && (
            <p className="nav-empty">No datasets yet. Upload one to get started.</p>
          )}
        </nav>
        <div className="sidebar-footer">
          <button className="btn-upload" onClick={() => setShowUpload(true)}>+ Upload Dataset</button>
          <div className="user-row">
            <span className="user-email">{userEmail}</span>
            <button className="btn-logout" onClick={onLogout}>Sign out</button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        {selected ? (
          <>
            <div className="content-header">
              <div>
                <h1 className="content-title">{selected.name}</h1>
                <p className="content-meta">
                  {selected.row_count != null ? `${fmt(selected.row_count, 0)} rows` : ""}
                  {selected.column_count != null ? ` · ${selected.column_count} columns` : ""}
                  {" · "}Uploaded {new Date(selected.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="header-actions">
                <StatusBadge status={selected.status} />
                <button
                  className="btn-danger"
                  onClick={async () => { await remove(selected.id); setSelected(null); }}
                >
                  Delete
                </button>
              </div>
            </div>
            {selected.status === "ready" ? (
              <AnalyticsPanel dataset={selected} />
            ) : selected.status === "failed" ? (
              <div className="panel-state panel-error">
                <p>Processing failed. Please delete and re-upload this dataset.</p>
              </div>
            ) : (
              <div className="panel-state">
                <div className="spinner" />
                <p>Dataset is {selected.status}… Refresh to check progress.</p>
                <button className="btn-ghost" onClick={refetch}>Refresh</button>
              </div>
            )}
          </>
        ) : (
          <div className="welcome-screen">
            <span className="welcome-icon">◈</span>
            <h2>Welcome to DataLens</h2>
            <p>Upload a dataset to start exploring KPIs, trends, and anomalies.</p>
            <button className="btn-primary" onClick={() => setShowUpload(true)}>Upload your first dataset</button>
          </div>
        )}
      </main>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUpload={async (f, n, d) => { await upload(f, n, d); setShowUpload(false); }}
        />
      )}
    </div>
  );
}
