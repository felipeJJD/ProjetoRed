-- Script para criar tabelas básicas no PostgreSQL do Railway

-- Criar tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    fullname TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verificar e inserir usuários padrão se não existirem
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'pedro') THEN
        INSERT INTO users (username, password, fullname)
        VALUES ('pedro', 'pbkdf2:sha256:260000$AXJn5lL3cFx5DuJJ$7cac3801538c9dea4d7a6177ee560dad9f5e1c0f6b976de1add4d3d1f4b48774', 'Pedro Administrador');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'felipe') THEN
        INSERT INTO users (username, password, fullname)
        VALUES ('felipe', 'pbkdf2:sha256:260000$zABnopQ3DkMPyZSz$5a14f1f16c4eacdb7601f93739b3e19a9e1d4e05f6b9a75af9ca8e73f7a3210e', 'Felipe Administrador');
    END IF;
END
$$;

-- Criar tabela de números WhatsApp
CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    phone_number TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    last_used TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Criar tabela de links personalizados
CREATE TABLE IF NOT EXISTS custom_links (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    link_name TEXT NOT NULL,
    custom_message TEXT,
    is_active INTEGER DEFAULT 1,
    click_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, link_name)
);

-- Criar tabela de logs de redirecionamento
CREATE TABLE IF NOT EXISTS redirect_logs (
    id SERIAL PRIMARY KEY,
    link_id INTEGER NOT NULL,
    number_id INTEGER NOT NULL,
    redirect_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (link_id) REFERENCES custom_links (id),
    FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id)
);

-- Criar links padrão para cada usuário
INSERT INTO custom_links (user_id, link_name, custom_message)
SELECT id, 'padrao', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...'
FROM users
WHERE NOT EXISTS (
    SELECT 1 FROM custom_links c WHERE c.user_id = users.id AND c.link_name = 'padrao'
);

-- Verificar tabelas criadas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verificar usuários
SELECT id, username, fullname FROM users; 