ALTER TABLE tasks
  ADD COLUMN description TEXT NULL AFTER text,
  ADD COLUMN due_date DATE NULL AFTER completed,
  ADD INDEX idx_tasks_due (due_date);

