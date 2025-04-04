-- Índices para melhorar performance das consultas PostgreSQL

-- Índices para tabela de usuários
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users (active);

-- Índices para tabela de números
CREATE INDEX IF NOT EXISTS idx_whatsapp_numbers_user_id ON whatsapp_numbers (user_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_numbers_active ON whatsapp_numbers (active);
CREATE INDEX IF NOT EXISTS idx_whatsapp_numbers_phone ON whatsapp_numbers (phone_number);
CREATE INDEX IF NOT EXISTS idx_whatsapp_numbers_last_used ON whatsapp_numbers (last_used);

-- Índices para tabela de links personalizados
CREATE INDEX IF NOT EXISTS idx_custom_links_user_id ON custom_links (user_id);
CREATE INDEX IF NOT EXISTS idx_custom_links_link_name ON custom_links (link_name);
CREATE INDEX IF NOT EXISTS idx_custom_links_user_link ON custom_links (user_id, link_name);
CREATE INDEX IF NOT EXISTS idx_custom_links_active ON custom_links (active);

-- Índices para tabela de logs de redirecionamento
CREATE INDEX IF NOT EXISTS idx_redirect_logs_time ON redirect_logs (redirect_time);
CREATE INDEX IF NOT EXISTS idx_redirect_logs_link_id ON redirect_logs (link_id);
CREATE INDEX IF NOT EXISTS idx_redirect_logs_number_id ON redirect_logs (number_id);
CREATE INDEX IF NOT EXISTS idx_redirect_logs_link_number ON redirect_logs (link_id, number_id);
CREATE INDEX IF NOT EXISTS idx_redirect_logs_user_id ON redirect_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_redirect_logs_date_trunc ON redirect_logs (DATE(redirect_time));
CREATE INDEX IF NOT EXISTS idx_redirect_logs_ip ON redirect_logs (ip_address);

-- Índice para busca de logs por geolocalização
CREATE INDEX IF NOT EXISTS idx_redirect_logs_geo ON redirect_logs (city, region, country);

-- Índice para a tabela de sessões
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions (expires);

-- Índice para a tabela de configurações
CREATE INDEX IF NOT EXISTS idx_settings_user_id ON settings (user_id);
CREATE INDEX IF NOT EXISTS idx_settings_setting_name ON settings (setting_name);

-- Comandos para analisar as tabelas após a criação dos índices
ANALYZE users;
ANALYZE whatsapp_numbers;
ANALYZE custom_links;
ANALYZE redirect_logs;
ANALYZE sessions;
ANALYZE settings;
