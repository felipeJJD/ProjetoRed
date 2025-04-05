#!/usr/bin/env python3
"""
Script para corrigir referências de endpoints no template dashboard.html
"""

template_path = 'templates/dashboard.html'

try:
    # Ler o arquivo
    with open(template_path, 'r') as file:
        content = file.read()
    
    # Substituir 'main.index' por 'index'
    updated_content = content.replace("url_for('main.index')", "url_for('index')")
    
    # Escrever alterações de volta ao arquivo
    with open(template_path, 'w') as file:
        file.write(updated_content)
    
    print(f"Arquivo {template_path} corrigido com sucesso.")
except Exception as e:
    print(f"Erro ao corrigir o arquivo: {str(e)}")
