-- Create shortener database and tables
USE shortener;

-- URLs table
CREATE TABLE IF NOT EXISTS urls (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  short_code VARCHAR(10) UNIQUE NOT NULL,
  long_url VARCHAR(2048) NOT NULL,
  user_id BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NULL,
  clicks INT DEFAULT 0,
  is_custom BOOLEAN DEFAULT FALSE,
  INDEX idx_short_code (short_code),
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at),
  INDEX idx_expires_at (expires_at)
);

-- Clicks analytics table
CREATE TABLE IF NOT EXISTS clicks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  short_code VARCHAR(10) NOT NULL,
  ip_address VARCHAR(45),
  user_agent VARCHAR(500),
  referrer VARCHAR(2048),
  clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_short_code (short_code),
  INDEX idx_clicked_at (clicked_at),
  INDEX idx_short_code_clicked_at (short_code, clicked_at),
  FOREIGN KEY (short_code) REFERENCES urls(short_code) ON DELETE CASCADE
);

-- Rate limiting table
CREATE TABLE IF NOT EXISTS rate_limits (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ip_address VARCHAR(45) UNIQUE NOT NULL,
  request_count INT DEFAULT 0,
  window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ip_address (ip_address),
  INDEX idx_window_start (window_start)
);

-- Create indexes for performance
ALTER TABLE urls ADD FULLTEXT INDEX ft_long_url (long_url);
ALTER TABLE clicks ADD INDEX idx_ip_address (ip_address);
ALTER TABLE clicks ADD INDEX idx_user_agent (user_agent);

-- Insert sample data (optional)
INSERT INTO urls (short_code, long_url, user_id, is_custom) VALUES
  ('demo1', 'https://www.github.com', 1, FALSE),
  ('demo2', 'https://www.stackoverflow.com', 1, FALSE),
  ('mylink', 'https://www.example.com/very/long/path?param=value', 1, TRUE)
ON DUPLICATE KEY UPDATE clicks = clicks;
