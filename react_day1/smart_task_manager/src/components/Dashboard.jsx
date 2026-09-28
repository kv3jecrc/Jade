import { useMemo } from "react";

/**
 * Dashboard
 * ---------
 * A small read-only summary strip above the task list. Purely derived
 * from `tasks` via useMemo -- no state of its own -- so it can never
 * drift out of sync with the real list.
 */
export default function Dashboard({ tasks }) {
  const stats = useMemo(() => {
    const total = tasks.length;
    const completed = tasks.filter((t) => t.completed).length;
    const pending = total - completed;
    const byPriority = { High: 0, Medium: 0, Low: 0 };
    for (const t of tasks) {
      if (byPriority[t.priority] !== undefined) byPriority[t.priority] += 1;
    }
    const completionRate = total === 0 ? 0 : Math.round((completed / total) * 100);
    return { total, completed, pending, byPriority, completionRate };
  }, [tasks]);

  return (
    <section className="dashboard" aria-label="Task summary">
      <div className="stat-card">
        <span className="stat-value">{stats.total}</span>
        <span className="stat-label">Total</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.pending}</span>
        <span className="stat-label">Pending</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.completed}</span>
        <span className="stat-label">Completed</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{stats.completionRate}%</span>
        <span className="stat-label">Done</span>
      </div>
      <div className="stat-card priority-breakdown">
        <div className="priority-row">
          <span className="priority-dot priority-high" /> High: {stats.byPriority.High}
        </div>
        <div className="priority-row">
          <span className="priority-dot priority-medium" /> Medium: {stats.byPriority.Medium}
        </div>
        <div className="priority-row">
          <span className="priority-dot priority-low" /> Low: {stats.byPriority.Low}
        </div>
      </div>
    </section>
  );
}
