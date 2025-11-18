# Análise: Melhor Solução para Banco de Dados no Lambda

## 📊 Situação Atual

- **Arquivo JSON**: 1.5MB com 5.571 municípios
- **Lambda**: Precisa carregar dados de municípios rapidamente
- **Frontend**: Espera rotas REST

## 🎯 Opções Analisadas

### 1. **JSON em Memória** (RECOMENDADO) ✅
**Prós:**
- Mais simples
- Sem dependências extras
- Cold start rápido (~100ms)
- 1.5MB é pequeno para Lambda (até 512MB RAM)
- JSON já parsado fica em memória entre invocações (warm start)

**Contras:**
- Busca linear (mas com 5.5k registros é rápido)

### 2. **SQLite**
**Prós:**
- SQL queries
- Índices para busca rápida

**Contras:**
- Precisa criar .db file (adiciona complexidade)
- Cold start mais lento
- Filesystem read/write no Lambda

### 3. **DynamoDB**
**Prós:**
- Serverless nativo
- Escalabilidade automática

**Contras:**
- Custo adicional
- Complexidade (precisa provisionar tabela)
- Overhead de latência de rede

### 4. **DuckDB**
**Prós:**
- In-memory analytics
- SQL queries rápidas

**Contras:**
- Binary grande (~50MB)
- Overkill para 5.5k registros

## ✅ Solução Recomendada: JSON + Cache em Memória

**Estratégia:**
1. Carregar `municipalities_db.json` no Lambda Layer ou dentro do ZIP
2. Parsear JSON na primeira invocação
3. Cache em memória global (persiste entre warm starts)
4. Criar índices em memória (dict por ID, por estado, etc.)

## 📝 Implementação

### Estrutura de Pastas
