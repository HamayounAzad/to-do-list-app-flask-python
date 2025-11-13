ALTER TABLE tasks
  ADD COLUMN category VARCHAR(64) NULL AFTER description,
  ADD COLUMN priority ENUM('low','medium','high') NOT NULL DEFAULT 'medium' AFTER due_date,
  ADD INDEX idx_tasks_category (category),
  ADD INDEX idx_tasks_priority (priority);

