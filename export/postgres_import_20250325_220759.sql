-- Script gerado para importação no PostgreSQL
-- Gerado em: 2025-03-25 22:07:59

BEGIN;

-- Tabela: whatsapp_numbers_old
CREATE TABLE IF NOT EXISTS whatsapp_numbers_old (
    id INTEGER,
    phone_number TEXT,
    description TEXT
);

-- Inserir dados na tabela whatsapp_numbers_old
INSERT INTO whatsapp_numbers_old (id, phone_number, description) VALUES (1, '5541987425246', 'meu');
INSERT INTO whatsapp_numbers_old (id, phone_number, description) VALUES (2, '5541999326949', 'segundo');
INSERT INTO whatsapp_numbers_old (id, phone_number, description) VALUES (4, '5521996544459', 'Pedrao');

-- Resetar sequência do ID para whatsapp_numbers_old
SELECT setval('whatsapp_numbers_old_id_seq', (SELECT MAX(id) FROM whatsapp_numbers_old));

-- Tabela: custom_links_old
CREATE TABLE IF NOT EXISTS custom_links_old (
    id INTEGER,
    link_name TEXT,
    is_active INTEGER,
    custom_message TEXT
);

-- Inserir dados na tabela custom_links_old
INSERT INTO custom_links_old (id, link_name, is_active, custom_message) VALUES (1, 'padrao', 1, NULL);
INSERT INTO custom_links_old (id, link_name, is_active, custom_message) VALUES (4, 'PedroTestefejao', 1, 'fala comigo bora fazer um fejao em 10 minutos');

-- Resetar sequência do ID para custom_links_old
SELECT setval('custom_links_old_id_seq', (SELECT MAX(id) FROM custom_links_old));

-- Tabela: users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER,
    username TEXT,
    password TEXT,
    fullname TEXT,
    created_at TIMESTAMP
);

-- Inserir dados na tabela users
INSERT INTO users (id, username, password, fullname, created_at) VALUES (1, 'pedro', 'pbkdf2:sha256:260000$XUrIYooGySouQAmr$8b4b906bcf42fbee26ac5c5f0869080238523fede11a0a859c8effd7bdc77ad9', 'Pedro Administrador', '2025-03-15 23:53:39');
INSERT INTO users (id, username, password, fullname, created_at) VALUES (2, 'felipe', 'pbkdf2:sha256:260000$bbESLujqRmdozHNn$0f6a4e5aa18547459040941b2d7d63dd8f8b9063f5c74f59d1f4619377d5afbc', 'Felipe Administrador', '2025-03-15 23:53:39');

-- Resetar sequência do ID para users
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- Tabela: custom_links
CREATE TABLE IF NOT EXISTS custom_links (
    id INTEGER,
    user_id INTEGER,
    link_name TEXT,
    custom_message TEXT,
    is_active INTEGER,
    click_count INTEGER
);

-- Inserir dados na tabela custom_links
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (1, 1, 'padrao', NULL, 1, 0);
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (4, 1, 'PedroTestefejao', 'fala comigo bora fazer um fejao em 10 minutos', 1, 0);
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (6, 2, 'padrao', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...', 1, 0);
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (31, 2, 'promocao', 'Você será redirecionado para um de nossos atendentes. Aguarde um momento...', 1, 11);

-- Resetar sequência do ID para custom_links
SELECT setval('custom_links_id_seq', (SELECT MAX(id) FROM custom_links));

-- Tabela: whatsapp_numbers
CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id INTEGER,
    user_id INTEGER,
    phone_number TEXT,
    description TEXT,
    redirect_count INTEGER,
    is_active INTEGER,
    last_used TIMESTAMP
);

-- Inserir dados na tabela whatsapp_numbers
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (1, 1, '5541987425246', 'meu', 0, 1, NULL);
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (2, 1, '5541999326949', 'segundo', 0, 1, NULL);
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (4, 1, '5521996544459', 'Pedrao', 0, 1, NULL);
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (6, 2, '5541999326949', '1', 3, 1, NULL);
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (7, 2, '5541987425246', '2', 3, 1, NULL);
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (8, 2, '5541999751082', '3', 5, 1, NULL);

-- Resetar sequência do ID para whatsapp_numbers
SELECT setval('whatsapp_numbers_id_seq', (SELECT MAX(id) FROM whatsapp_numbers));

-- Tabela: redirects
CREATE TABLE IF NOT EXISTS redirects (
    id INTEGER,
    number_id INTEGER,
    link_id INTEGER,
    timestamp TIMESTAMP
);

-- Inserir dados na tabela redirects
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (1, 8, 31, '2025-03-16 00:52:37');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (2, 6, 31, '2025-03-16 00:52:55');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (3, 6, 31, '2025-03-16 00:53:01');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (4, 7, 31, '2025-03-16 00:53:53');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (5, 7, 31, '2025-03-16 00:53:53');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (6, 8, 31, '2025-03-16 00:53:59');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (7, 8, 31, '2025-03-16 00:54:00');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (8, 7, 31, '2025-03-16 00:54:05');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (9, 8, 31, '2025-03-16 00:54:06');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (10, 8, 31, '2025-03-16 00:54:12');
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (11, 6, 31, '2025-03-16 00:54:13');

-- Resetar sequência do ID para redirects
SELECT setval('redirects_id_seq', (SELECT MAX(id) FROM redirects));

-- Tabela: redirect_logs
CREATE TABLE IF NOT EXISTS redirect_logs (
    id INTEGER,
    link_id INTEGER,
    number_id INTEGER,
    redirect_time TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);

-- Resetar sequência do ID para redirect_logs
SELECT setval('redirect_logs_id_seq', (SELECT MAX(id) FROM redirect_logs));

COMMIT;
