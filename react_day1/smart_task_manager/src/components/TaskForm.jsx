import { useState } from "react";

/**
 * TaskForm
 * --------
 * Controlled form (useState for each field) for adding a new task.
 * Calls `onAddTask({ title, priority })` and clears itself on submit.
 */
export default function TaskForm({ onAddTask }) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setError("Please enter a task title.");
      return;
    }
    onAddTask({ title: trimmed, priority });
    setTitle("");
    setPriority("Medium");
    setError("");
  };

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        type="text"
        className="task-title-input"
        placeholder="What needs to be done?"
        value={title}
        onChange={(e) => {
          setTitle(e.target.value);
          if (error) setError("");
        }}
        aria-label="Task title"
      />
      <select
        className="priority-select"
        value={priority}
        onChange={(e) => setPriority(e.target.value)}
        aria-label="Task priority"
      >
        <option value="High">High</option>
        <option value="Medium">Medium</option>
        <option value="Low">Low</option>
      </select>
      <button type="submit" className="add-task-btn">
        Add Task
      </button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </form>
  );
}
