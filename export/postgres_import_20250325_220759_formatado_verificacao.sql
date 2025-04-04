-- Script para verificar se as tabelas foram criadas corretamente

-- Listar todas as tabelas
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Contar registros na tabela whatsapp_numbers_old
SELECT 'whatsapp_numbers_old' AS tabela, COUNT(*) AS registros FROM whatsapp_numbers_old;

-- Contar registros na tabela custom_links_old
SELECT 'custom_links_old' AS tabela, COUNT(*) AS registros FROM custom_links_old;

-- Contar registros na tabela users
SELECT 'users' AS tabela, COUNT(*) AS registros FROM users;

-- Contar registros na tabela custom_links
SELECT 'custom_links' AS tabela, COUNT(*) AS registros FROM custom_links;

-- Contar registros na tabela whatsapp_numbers
SELECT 'whatsapp_numbers' AS tabela, COUNT(*) AS registros FROM whatsapp_numbers;

-- Contar registros na tabela redirects
SELECT 'redirects' AS tabela, COUNT(*) AS registros FROM redirects;

-- Contar registros na tabela redirect_logs
SELECT 'redirect_logs' AS tabela, COUNT(*) AS registros FROM redirect_logs;

-- Verificar usuários
SELECT id, username, fullname FROM users;

