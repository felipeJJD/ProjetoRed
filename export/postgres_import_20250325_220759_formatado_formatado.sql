-- Comando 1
BEGIN;

-- Comando 2
CREATE TABLE IF NOT EXISTS whatsapp_numbers_old (
    id INTEGER,
    phone_number TEXT,
    description TEXT
);

-- Comando 3
INSERT INTO whatsapp_numbers_old (id, phone_number, description) VALUES (1, '5541987425246', 'meu');

-- Comando 4
INSERT INTO whatsapp_numbers_old (id, phone_number, description) VALUES (2, '5541999326949', 'segundo');

-- Comando 5
INSERT INTO whatsapp_numbers_old (id, phone_number, description) VALUES (4, '5521996544459', 'Pedrao');

-- Comando 6
SELECT setval('whatsapp_numbers_old_id_seq', (SELECT MAX(id) FROM whatsapp_numbers_old));

-- Comando 7
CREATE TABLE IF NOT EXISTS custom_links_old (
    id INTEGER,
    link_name TEXT,
    is_active INTEGER,
    custom_message TEXT
);

-- Comando 8
INSERT INTO custom_links_old (id, link_name, is_active, custom_message) VALUES (1, 'padrao', 1, NULL);

-- Comando 9
INSERT INTO custom_links_old (id, link_name, is_active, custom_message) VALUES (4, 'PedroTestefejao', 1, 'fala comigo bora fazer um fejao em 10 minutos');

-- Comando 10
SELECT setval('custom_links_old_id_seq', (SELECT MAX(id) FROM custom_links_old));

-- Comando 11
CREATE TABLE IF NOT EXISTS users (
    id INTEGER,
    username TEXT,
    password TEXT,
    fullname TEXT,
    created_at TIMESTAMP
);

-- Comando 12
INSERT INTO users (id, username, password, fullname, created_at) VALUES (1, 'pedro', 'pbkdf2:sha256:260000$XUrIYooGySouQAmr$8b4b906bcf42fbee26ac5c5f0869080238523fede11a0a859c8effd7bdc77ad9', 'Pedro Administrador', '2025-03-15 23:53:39');

-- Comando 13
INSERT INTO users (id, username, password, fullname, created_at) VALUES (2, 'felipe', 'pbkdf2:sha256:260000$bbESLujqRmdozHNn$0f6a4e5aa18547459040941b2d7d63dd8f8b9063f5c74f59d1f4619377d5afbc', 'Felipe Administrador', '2025-03-15 23:53:39');

-- Comando 14
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- Comando 15
CREATE TABLE IF NOT EXISTS custom_links (
    id INTEGER,
    user_id INTEGER,
    link_name TEXT,
    custom_message TEXT,
    is_active INTEGER,
    click_count INTEGER
);

-- Comando 16
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (1, 1, 'padrao', NULL, 1, 0);

-- Comando 17
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (4, 1, 'PedroTestefejao', 'fala comigo bora fazer um fejao em 10 minutos', 1, 0);

-- Comando 18
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (6, 2, 'padrao', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...', 1, 0);

-- Comando 19
INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, click_count) VALUES (31, 2, 'promocao', 'Você será redirecionado para um de nossos atendentes. Aguarde um momento...', 1, 11);

-- Comando 20
SELECT setval('custom_links_id_seq', (SELECT MAX(id) FROM custom_links));

-- Comando 21
CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id INTEGER,
    user_id INTEGER,
    phone_number TEXT,
    description TEXT,
    redirect_count INTEGER,
    is_active INTEGER,
    last_used TIMESTAMP
);

-- Comando 22
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (1, 1, '5541987425246', 'meu', 0, 1, NULL);

-- Comando 23
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (2, 1, '5541999326949', 'segundo', 0, 1, NULL);

-- Comando 24
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (4, 1, '5521996544459', 'Pedrao', 0, 1, NULL);

-- Comando 25
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (6, 2, '5541999326949', '1', 3, 1, NULL);

-- Comando 26
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (7, 2, '5541987425246', '2', 3, 1, NULL);

-- Comando 27
INSERT INTO whatsapp_numbers (id, user_id, phone_number, description, redirect_count, is_active, last_used) VALUES (8, 2, '5541999751082', '3', 5, 1, NULL);

-- Comando 28
SELECT setval('whatsapp_numbers_id_seq', (SELECT MAX(id) FROM whatsapp_numbers));

-- Comando 29
CREATE TABLE IF NOT EXISTS redirects (
    id INTEGER,
    number_id INTEGER,
    link_id INTEGER,
    timestamp TIMESTAMP
);

-- Comando 30
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (1, 8, 31, '2025-03-16 00:52:37');

-- Comando 31
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (2, 6, 31, '2025-03-16 00:52:55');

-- Comando 32
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (3, 6, 31, '2025-03-16 00:53:01');

-- Comando 33
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (4, 7, 31, '2025-03-16 00:53:53');

-- Comando 34
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (5, 7, 31, '2025-03-16 00:53:53');

-- Comando 35
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (6, 8, 31, '2025-03-16 00:53:59');

-- Comando 36
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (7, 8, 31, '2025-03-16 00:54:00');

-- Comando 37
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (8, 7, 31, '2025-03-16 00:54:05');

-- Comando 38
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (9, 8, 31, '2025-03-16 00:54:06');

-- Comando 39
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (10, 8, 31, '2025-03-16 00:54:12');

-- Comando 40
INSERT INTO redirects (id, number_id, link_id, timestamp) VALUES (11, 6, 31, '2025-03-16 00:54:13');

-- Comando 41
SELECT setval('redirects_id_seq', (SELECT MAX(id) FROM redirects));

-- Comando 42
CREATE TABLE IF NOT EXISTS redirect_logs (
    id INTEGER,
    link_id INTEGER,
    number_id INTEGER,
    redirect_time TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);

-- Comando 43
SELECT setval('redirect_logs_id_seq', (SELECT MAX(id) FROM redirect_logs));

-- Comando 44
COMMIT;

