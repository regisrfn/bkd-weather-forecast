# 🚀 Scripts de Deploy

## Script Principal ✨

### `deploy-main.sh` - Deploy Completo em Um Único Script

**Uso:**
```bash
bash scripts/deploy-main.sh
```

**O que faz:**
1. ✅ **Validações iniciais** - Verifica arquivos necessários
2. 🧪 **Testes unitários** - Roda antes do build
3. 📦 **Build inteligente** - Detecta TODOS os arquivos .py recursivamente
4. 🔍 **Validação do ZIP** - Verifica arquivos críticos
5. 🔧 **Terraform** - Init, validate, plan, apply
6. 🚀 **Deploy AWS** - Atualiza Lambda e API Gateway
7. 🧪 **Testes de integração** - Valida API após deploy
8. 📊 **Resumo final** - Mostra status e URL da API

**Vantagens:**
- ✅ Detecta automaticamente todos os arquivos Python
- ✅ Não precisa atualizar quando adiciona novos arquivos
- ✅ Validação completa do pacote antes do deploy
- ✅ Feedback visual com cores e emojis
- ✅ Tudo em um único comando

---

## Scripts Auxiliares

### `load_env.sh` - Carrega Variáveis de Ambiente

Carrega variáveis do arquivo `.env` para o ambiente atual.

### `run_tests.sh` - Executa Testes

Executa testes unitários ou de integração.

```bash
bash scripts/run_tests.sh unit
bash scripts/run_tests.sh integration
```

---

## Comparação: Detecção de Arquivos

### ✅ Método Atual (Automático)
```bash
# Detecta automaticamente TODOS os .py
find "${LAMBDA_DIR}" -name "*.py" -exec cp {} "${PACKAGE_DIR}/" \;

# Copia todos os diretórios necessários
for dir in domain application infrastructure shared data; do
    cp -r "${LAMBDA_DIR}/${dir}" "${PACKAGE_DIR}/"
done

# Lista arquivos encontrados
find "${PACKAGE_DIR}" -name "*.py" | wc -l
# Resultado: 31 arquivos da aplicação + 730 das dependências ✓
```

**Vantagens:**
- ✅ Detecta automaticamente novos arquivos
- ✅ Não precisa atualizar o script ao adicionar código
- ✅ Valida arquivos críticos antes do deploy
- ✅ Feedback visual completo

---

## Exemplo de Saída

```
🚀 Deploy Lambda Weather Forecast (Unificado)
==============================================

🔍 FASE 0: Validações Iniciais
=================================
✓ terraform.tfvars encontrado
✓ requirements.txt encontrado
✓ Variáveis de ambiente carregadas

🧪 FASE 1: Testes Unitários (Pré-Build)
========================================
✅ Todos os testes unitários passaram!

📦 FASE 2: Build do Pacote Lambda
====================================
🧹 Limpando build anterior...
✓ Diretório limpo

📥 Instalando dependências Python...
✓ Dependências instaladas

📂 Copiando código da aplicação (método recursivo)...
   → Copiando arquivos .py da raiz...
   → Copiando diretórios...
      ✓ domain
      ✓ application
      ✓ infrastructure
      ✓ shared
      ✓ data

📋 Arquivos Python detectados:
   15 arquivos .py copiados

📄 Exemplo de arquivos copiados:
   ✓ lambda_function.py
   ✓ config.py
   ✓ domain/__init__.py
   ✓ domain/entities/__init__.py
   ✓ domain/entities/city.py
   ✓ domain/entities/weather.py
   ...

🗑️  Removendo arquivos desnecessários...
✓ Limpeza concluída

📦 Criando arquivo ZIP...
✓ ZIP criado: 15M
   📍 Local: terraform/build/lambda_function.zip

🔍 Verificando arquivos críticos no ZIP...
   ✓ lambda_function.py
   ✓ config.py
   ✓ domain/entities/city.py
   ✓ domain/entities/weather.py
   ✓ application/use_cases/get_city_weather.py
   ✓ infrastructure/repositories/weather_repository.py
   ✓ data/municipalities_db.json

✅ Pacote Lambda validado com sucesso!

🔧 FASE 3: Configuração Terraform
===================================
Inicializando Terraform...
✓ Configuração válida

🚀 FASE 4: Deploy na AWS
==========================
✅ Deploy na AWS concluído!

📊 FASE 5: Outputs e Validação
================================
🌐 API URL: https://xxxxx.execute-api.us-east-1.amazonaws.com/dev/
   (Salvo em API_URL.txt)

🧪 Executando Testes de Integração...
✅ Todos os testes de integração passaram!

═══════════════════════════════════════
🎉 Deploy Finalizado com Sucesso!
═══════════════════════════════════════
✓ Testes unitários (pré-build)
✓ Build do pacote Lambda (15M)
✓ Deploy AWS (Terraform)
✓ Testes de integração (pós-deploy)
```

---

## Como Usar

**Deploy completo:**
```bash
bash scripts/deploy-main.sh
```

**Apenas testes:**
```bash
bash scripts/run_tests.sh unit
```

---

## Troubleshooting

### Arquivos não encontrados no ZIP?

O script novo lista automaticamente:
```bash
📋 Arquivos Python detectados:
   15 arquivos .py copiados

📄 Exemplo de arquivos copiados (primeiros 15):
   ✓ lambda_function.py
   ...
```

Se algum arquivo crítico faltar, o script para com erro antes do deploy:
```bash
❌ Erro: Arquivos críticos faltando no ZIP!
   ✗ domain/entities/weather.py (FALTANDO!)
```

### Dependências faltando?

O script verifica:
```bash
🔍 Verificando dependências Python...
   ✓ aws_lambda_powertools
   ✓ requests
   ✓ botocore
```

---

## Estrutura dos Scripts

```
scripts/
├── deploy-main.sh       ← Script principal de deploy
├── run_tests.sh         ← Executar testes
├── load_env.sh          ← Carregar variáveis de ambiente
├── DEPLOY_README.md     ← Esta documentação
└── build/               ← Diretório temporário (gerado)
```
