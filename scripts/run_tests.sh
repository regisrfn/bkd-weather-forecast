#!/bin/bash
# Script para executar testes com variáveis de ambiente
# Execute da raiz do projeto: bash scripts/run_tests.sh [unit|integration|pre-deploy|post-deploy|all]
#
# Opções:
#   unit        - Apenas testes unitários (29 testes)
#   integration - Todos os testes de integração (8 testes)
#   pre-deploy  - Testes unitários + integração pré-deploy (37 testes) - usado no deploy-main.sh
#   post-deploy - Testes de API Gateway (requer API_GATEWAY_URL ou API_URL.txt)
#   all         - Todos os testes (37 testes)
#   (vazio)     - Padrão: todos os testes

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

# Configurar PYTHONPATH para incluir o diretório lambda
export PYTHONPATH="${PWD}/lambda:${PYTHONPATH}"

# Executar testes
echo ""
echo "🧪 Executando testes..."
echo ""

if [ "$1" == "unit" ]; then
    python -m pytest lambda/tests/unit/ -v
elif [ "$1" == "integration" ]; then
    python -m pytest lambda/tests/integration/ -v
elif [ "$1" == "pre-deploy" ]; then
    echo "=== TESTES UNITÁRIOS ==="
    python -m pytest lambda/tests/unit/ -v
    echo ""
    echo "=== TESTES DE INTEGRAÇÃO (Pré-Deploy) ==="
    python -m pytest lambda/tests/integration/pre_deploy/ -v
elif [ "$1" == "post-deploy" ]; then
    echo "=== TESTES DE API GATEWAY (Pós-Deploy) ==="
    if [ -z "$API_GATEWAY_URL" ]; then
        echo "⚠️  API_GATEWAY_URL não definida. Tentando ler de API_URL.txt..."
        if [ -f "API_URL.txt" ]; then
            export API_GATEWAY_URL=$(cat API_URL.txt)
            echo "✅ URL carregada: $API_GATEWAY_URL"
        else
            echo "❌ API_URL.txt não encontrado. Defina API_GATEWAY_URL manualmente."
            exit 1
        fi
    fi
    python -m pytest lambda/tests/integration/post_deploy/ -v
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
