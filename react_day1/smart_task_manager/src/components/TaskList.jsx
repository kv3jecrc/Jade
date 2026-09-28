import TaskItem from "./TaskItem";

export default function TaskList({ tasks, onToggleComplete, onDelete }) {
  if (tasks.length === 0) {
    return <p className="empty-state">No tasks match your search/filter. Add one above!</p>;
  }

  return (
    <ul className="task-list">
      {tasks.map((task) => (
        <TaskItem
          key={task.id}
          task={task}
          onToggleComplete={onToggleComplete}
          onDelete={onDelete}
        />
      ))}
    </ul>
  );
}
