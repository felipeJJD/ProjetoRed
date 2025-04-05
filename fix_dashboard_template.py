#!/usr/bin/env python3
"""
Script para corrigir referências de endpoints no template dashboard.html
"""

template_path = 'templates/dashboard.html'

try:
    # Ler o arquivo
    with open(template_path, 'r') as file:
        content = file.read()
    
    # Substituir 'admin_backup' por 'admin.admin_backup'
    updated_content = content.replace("url_for('admin_backup')", "url_for('admin.admin_backup')")
    
    # Escrever alterações de volta ao arquivo
    with open(template_path, 'w') as file:
        file.write(updated_content)
    
    print(f"Arquivo {template_path} corrigido com sucesso.")
except Exception as e:
    print(f"Erro ao corrigir o arquivo: {str(e)}")
