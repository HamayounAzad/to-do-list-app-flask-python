ALTER TABLE tasks
  ADD COLUMN assigned_to INT NULL AFTER user_id,
  ADD INDEX idx_tasks_assigned (assigned_to),
  ADD CONSTRAINT fk_tasks_assigned FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL;

