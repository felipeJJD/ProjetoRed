#!/usr/bin/env python3
"""
Script para corrigir referências de endpoints nos templates após a migração para blueprints
"""
import os

def fix_template_references(file_path, old_pattern, new_pattern):
    """Substitui referências de endpoint em um arquivo de template"""
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            print(f"Arquivo não encontrado: {file_path}")
            return False
        
        # Ler o arquivo
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Substituir o padrão
        updated_content = content.replace(old_pattern, new_pattern)
        
        # Se não houve alterações, não reescrever o arquivo
        if content == updated_content:
            print(f"Nenhuma alteração necessária em: {file_path}")
            return False
        
        # Escrever alterações de volta ao arquivo
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print(f"Arquivo {file_path} corrigido com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao corrigir o arquivo {file_path}: {str(e)}")
        return False

# Lista de correções a serem aplicadas (arquivo, padrão antigo, novo padrão)
corrections = [
    # Corrigir referências a 'administracao'
    ('templates/admin_usuarios.html', "url_for('administracao')", "url_for('admin.administracao')"),
    
    # Corrigir referências a 'dashboard'
    ('templates/admin.html', "url_for('dashboard')", "url_for('admin.dashboard')"),
    ('templates/admin/index.html', "url_for('dashboard')", "url_for('admin.dashboard')"),
    ('templates/administracao.html', "url_for('dashboard')", "url_for('admin.dashboard')"),
    ('templates/admin_usuarios.html', "url_for('dashboard')", "url_for('admin.dashboard')"),
    
    # Corrigir referências a 'logout'
    ('templates/admin.html', "url_for('logout')", "url_for('auth.logout')"),
    ('templates/admin/index.html', "url_for('logout')", "url_for('auth.logout')"),
    ('templates/administracao.html', "url_for('logout')", "url_for('auth.logout')"),
    ('templates/admin_usuarios.html', "url_for('logout')", "url_for('auth.logout')"),
]

# Aplicar as correções
successes = 0
failures = 0

for file_path, old_pattern, new_pattern in corrections:
    if fix_template_references(file_path, old_pattern, new_pattern):
        successes += 1
    else:
        failures += 1

print(f"\nResumo: {successes} arquivos corrigidos, {failures} falhas ou arquivos sem alterações necessárias.")
