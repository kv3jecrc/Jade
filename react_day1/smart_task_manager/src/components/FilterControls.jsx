const FILTERS = ["All", "Pending", "Completed"];

export default function FilterControls({ activeFilter, onChange }) {
  return (
    <div className="filter-controls" role="group" aria-label="Filter tasks">
      {FILTERS.map((filter) => (
        <button
          key={filter}
          className={`filter-btn ${activeFilter === filter ? "active" : ""}`}
          onClick={() => onChange(filter)}
          aria-pressed={activeFilter === filter}
        >
          {filter}
        </button>
      ))}
    </div>
  );
}
