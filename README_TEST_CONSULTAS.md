# Script de Teste de Consistência de Dados

Este script foi criado para testar a consistência dos dados no sistema de redirecionamento, especificamente para verificar se há discrepâncias entre as contagens de "acessos a chip", resultados no mapa e atividades recentes.

## Funcionalidades

- **Teste de consistência**: Compara os totais entre diferentes consultas para garantir que todos retornem o mesmo número de acessos.
- **Identificação de registros órfãos**: Encontra redirecionamentos que apontam para números de WhatsApp que não existem mais.
- **Correção de inconsistências**: Pode corrigir automaticamente registros órfãos, atribuindo-os a números válidos.
- **Teste específico 15 a 15**: Testa especificamente o período do dia 15 de um mês ao dia 15 do mês seguinte.

## Requisitos

- Python 3.6 ou superior
- Acesso ao arquivo de banco de dados `instance/whatsapp_redirect.db`

## Como Usar

O script pode ser executado diretamente pela linha de comando:

```bash
python test_consultas.py [opções]
```

ou, se o script for executável:

```bash
./test_consultas.py [opções]
```

### Parâmetros disponíveis

| Parâmetro | Descrição |
|-----------|-----------|
| `--user ID` | ID do usuário a ser testado (padrão: 1) |
| `--link ID` | ID do link específico a ser testado (padrão: 'all' para todos) |
| `--fix` | Corrige registros órfãos automaticamente |
| `--start-date DATA` | Data inicial para o filtro no formato AAAA-MM-DD |
| `--end-date DATA` | Data final para o filtro no formato AAAA-MM-DD |
| `--test-15-to-15` | Testa especificamente o período de 15 a 15 |
| `--month MÊS` | Mês para teste 15-15 (1-12) |
| `--year ANO` | Ano para teste 15-15 |

### Exemplos de uso

1. Testar período de 15 a 15 para o mês atual:
```bash
python test_consultas.py --test-15-to-15
```

2. Testar um período específico:
```bash
python test_consultas.py --start-date 2023-01-01 --end-date 2023-01-31
```

3. Corrigir registros órfãos:
```bash
python test_consultas.py --fix
```

4. Testar um link específico:
```bash
python test_consultas.py --link 2 --start-date 2023-01-01 --end-date 2023-01-31
```

## Interpretação dos Resultados

O script exibirá os seguintes resultados:

1. **Total de redirecionamentos (logs brutos)**: Contagem de todos os logs de redirecionamento.
2. **Total de redirecionamentos com números válidos**: Contagem dos logs que possuem referência a números válidos.
3. **Soma de acessos por chip**: Soma dos acessos agrupados por número de telefone.
4. **Total de acessos no mapa**: Contagem de acessos que apareceriam no mapa.

Se todos os valores forem iguais, os dados estão consistentes. Se houver discrepâncias, o script identificará onde estão as diferenças e possíveis registros órfãos.

## Resolução de Problemas

Se forem encontradas discrepâncias entre as contagens:

1. Verifique se há registros órfãos executando:
```bash
python test_consultas.py --fix
```

2. Se as discrepâncias persistirem, pode ser necessário verificar o banco de dados diretamente:
```bash
sqlite3 instance/whatsapp_redirect.db
```

3. Execute o script novamente após as correções para confirmar que os problemas foram resolvidos.

## Notas Adicionais

- O script faz backup automático dos registros corrigidos.
- Todas as operações são registradas em detalhes no console.
- A correção de registros órfãos tentará primeiro atribuí-los a números válidos antes de considerá-los para remoção. 