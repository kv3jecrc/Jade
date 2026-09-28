export default function TaskItem({ task, onToggleComplete, onDelete }) {
  return (
    <li className={`task-item priority-border-${task.priority.toLowerCase()}`}>
      <label className="task-checkbox-label">
        <input
          type="checkbox"
          checked={task.completed}
          onChange={() => onToggleComplete(task.id)}
          aria-label={`Mark "${task.title}" as ${task.completed ? "pending" : "completed"}`}
        />
        <span className={`task-title ${task.completed ? "completed" : ""}`}>
          {task.title}
        </span>
      </label>

      <span className={`priority-badge priority-${task.priority.toLowerCase()}`}>
        {task.priority}
      </span>

      <span className={`status-badge ${task.completed ? "status-completed" : "status-pending"}`}>
        {task.completed ? "Completed" : "Pending"}
      </span>

      <button
        className="delete-btn"
        onClick={() => onDelete(task.id)}
        aria-label={`Delete "${task.title}"`}
        title="Delete task"
      >
        ✕
      </button>
    </li>
  );
}
