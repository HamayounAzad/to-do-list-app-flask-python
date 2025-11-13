ALTER TABLE users
  ADD COLUMN display_name VARCHAR(64) NULL AFTER username,
  ADD COLUMN avatar_url VARCHAR(255) NULL AFTER email;

