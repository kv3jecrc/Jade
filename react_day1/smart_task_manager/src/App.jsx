import { useState, useMemo, useCallback } from "react";
import { ThemeProvider } from "./context/ThemeContext";
import useLocalStorage from "./hooks/useLocalStorage";
import ThemeToggle from "./components/ThemeToggle";
import Dashboard from "./components/Dashboard";
import TaskForm from "./components/TaskForm";
import SearchBar from "./components/SearchBar";
import FilterControls from "./components/FilterControls";
import TaskList from "./components/TaskList";
import "./App.css";

let idCounter = 0;
function nextId() {
  idCounter += 1;
  return `${Date.now()}-${idCounter}`;
}

function TaskManager() {
  // Source of truth for all tasks, persisted to localStorage so a
  // refresh doesn't lose the list.
  const [tasks, setTasks] = useLocalStorage("smart-task-manager:tasks", []);

  // UI-only state: doesn't need to survive a refresh, so plain useState.
  const [searchTerm, setSearchTerm] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");

  const handleAddTask = useCallback(
    ({ title, priority }) => {
      setTasks((prev) => [
        ...prev,
        { id: nextId(), title, priority, completed: false },
      ]);
    },
    [setTasks]
  );

  const handleToggleComplete = useCallback(
    (id) => {
      setTasks((prev) =>
        prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
      );
    },
    [setTasks]
  );

  const handleDelete = useCallback(
    (id) => {
      setTasks((prev) => prev.filter((t) => t.id !== id));
    },
    [setTasks]
  );

  // Derived view: search + filter applied, recomputed only when their
  // inputs change (avoids re-filtering on every unrelated re-render).
  const visibleTasks = useMemo(() => {
    let result = tasks;

    if (activeFilter === "Completed") {
      result = result.filter((t) => t.completed);
    } else if (activeFilter === "Pending") {
      result = result.filter((t) => !t.completed);
    }

    const term = searchTerm.trim().toLowerCase();
    if (term) {
      result = result.filter((t) => t.title.toLowerCase().includes(term));
    }

    return result;
  }, [tasks, activeFilter, searchTerm]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Smart Task Manager</h1>
        <ThemeToggle />
      </header>

      <Dashboard tasks={tasks} />

      <TaskForm onAddTask={handleAddTask} />

      <div className="controls-row">
        <SearchBar value={searchTerm} onChange={setSearchTerm} />
        <FilterControls activeFilter={activeFilter} onChange={setActiveFilter} />
      </div>

      <TaskList
        tasks={visibleTasks}
        onToggleComplete={handleToggleComplete}
        onDelete={handleDelete}
      />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <TaskManager />
    </ThemeProvider>
  );
}
