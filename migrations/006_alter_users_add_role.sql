ALTER TABLE users
  ADD COLUMN role ENUM('user','admin') NOT NULL DEFAULT 'user' AFTER password_hash;
SET @min_id := (SELECT MIN(id) FROM users);
UPDATE users SET role = 'admin' WHERE id = @min_id;
