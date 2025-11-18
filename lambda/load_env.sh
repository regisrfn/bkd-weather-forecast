#!/bin/bash
# Script para carregar variáveis de ambiente do .env
# Uso: source load_env.sh

ENV_FILE="../.env"

if [ -f "$ENV_FILE" ]; then
    echo "🔄 Carregando variáveis de $ENV_FILE..."
    
    # Ler o arquivo .env e exportar cada variável
    while IFS='=' read -r key value; do
        # Ignorar comentários e linhas vazias
        if [[ ! "$key" =~ ^#.* ]] && [[ -n "$key" ]]; then
            # Remover espaços e aspas
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")
            
            # Exportar a variável
            export "$key=$value"
            
            # Mostrar confirmação (ocultando valor sensível)
            if [[ "$key" == *"KEY"* ]] || [[ "$key" == *"SECRET"* ]]; then
                echo "  ✅ $key=***${value: -4}"
            else
                echo "  ✅ $key=$value"
            fi
        fi
    done < "$ENV_FILE"
    
    echo "✅ Variáveis carregadas com sucesso!"
else
    echo "❌ Arquivo $ENV_FILE não encontrado!"
    exit 1
fi
