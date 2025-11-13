ALTER TABLE users
  MODIFY COLUMN role ENUM('user','admin','customer') NOT NULL DEFAULT 'customer';

