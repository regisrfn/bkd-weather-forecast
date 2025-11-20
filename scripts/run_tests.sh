#!/bin/bash
# Script para executar testes com variáveis de ambiente
# Execute da raiz do projeto: bash scripts/run_tests.sh [unit|integration|all]

# Ir para o diretório raiz do projeto
cd "$(dirname "$0")/.."

# Carregar variáveis de ambiente se .env existir
if [ -f ".env" ]; then
    echo "🔄 Carregando variáveis de ambiente..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Variáveis carregadas!"
elif [ -f "lambda/.env" ]; then
    echo "🔄 Carregando variáveis de ambiente de lambda/.env..."
    export $(cat lambda/.env | grep -v '^#' | xargs)
    echo "✅ Variáveis carregadas!"
else
    echo "⚠️  Nenhum arquivo .env encontrado, usando valores padrão para testes"
    export OPENWEATHER_API_KEY="${OPENWEATHER_API_KEY:-test_key}"
fi

# Ativar ambiente virtual
source .venv/bin/activate

# Executar testes
echo ""
echo "🧪 Executando testes..."
echo ""

if [ "$1" == "unit" ]; then
    python -m pytest lambda/tests/unit/ -v
elif [ "$1" == "integration" ]; then
    python -m pytest lambda/tests/integration/ -v
elif [ "$1" == "all" ]; then
    echo "=== TESTES UNITÁRIOS ==="
    python -m pytest lambda/tests/unit/ -v
    echo ""
    echo "=== TESTES DE INTEGRAÇÃO ==="
    python -m pytest lambda/tests/integration/ -v
else
    # Se nenhum argumento, executar todos
    echo "=== TESTES UNITÁRIOS ==="
    python -m pytest lambda/tests/unit/ -v
    echo ""
    echo "=== TESTES DE INTEGRAÇÃO ==="
    python -m pytest lambda/tests/integration/ -v
fi
