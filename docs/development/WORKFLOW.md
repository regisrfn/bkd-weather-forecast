# Development Workflow Guide

## Visão Geral

Guia completo para desenvolver, testar e deployar a aplicação Weather Forecast API.

**Stack de Desenvolvimento:**
- Python 3.13
- AWS Lambda + API Gateway
- Terraform (IaC)
- pytest (Testing)
- AWS CLI
- Git

---

## Setup Inicial

### 1. Pré-requisitos

```bash
# Verificar versões
python3 --version  # Python 3.13+
terraform --version  # Terraform 1.0+
aws --version  # AWS CLI 2.0+
git --version  # Git 2.0+

# Instalar Python 3.13 (Ubuntu/Debian)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 python3.13-venv python3.13-dev

# Instalar Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Instalar AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### 2. Clonar Repositório

```bash
# Clone repository
git clone https://github.com/regisrfn/bkd-weather-forecast.git
cd bkd-weather-forecast

# Checkout branch
git checkout -b feature/my-feature
```

### 3. Configurar Python Environment

```bash
# Criar virtual environment
cd lambda
python3.13 -m venv .venv

# Ativar environment
source .venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verificar instalação
python --version  # Python 3.13
pytest --version  # pytest 8.3.4
```

### 4. Configurar AWS Credentials

```bash
# Configurar AWS CLI
aws configure

# Input:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: sa-east-1
# Default output format: json

# Verificar credenciais
aws sts get-caller-identity
```

### 5. Environment Variables

```bash
# Criar .env file
cat > .env << EOF
OPENWEATHER_API_KEY=your_api_key_here
DYNAMODB_CACHE_TABLE=weather-forecast-cache-dev
AWS_DEFAULT_REGION=sa-east-1
AWS_PROFILE=default
ENVIRONMENT=dev
EOF

# Load environment variables
source .env

# Ou use direnv (recomendado)
echo "export OPENWEATHER_API_KEY=your_key" > .envrc
direnv allow
```

---

## Development Workflow

### 1. Feature Development

```bash
# 1. Criar branch feature
git checkout -b feature/add-new-endpoint

# 2. Fazer mudanças no código
vim lambda/application/use_cases/new_use_case.py

# 3. Escrever testes
vim lambda/tests/unit/test_new_use_case.py

# 4. Rodar testes localmente
pytest lambda/tests/unit/test_new_use_case.py -v

# 5. Verificar todos os testes
pytest lambda/tests/ -v

# 6. Commit mudanças
git add .
git commit -m "feat: add new endpoint for X"

# 7. Push para remote
git push origin feature/add-new-endpoint

# 8. Criar Pull Request
# Via GitHub UI ou gh CLI
gh pr create --title "Add new endpoint" --body "Description"
```

### 2. Local Testing

```bash
# Ativar virtual environment
source .venv/bin/activate

# Run unit tests
pytest lambda/tests/unit/ -v

# Run integration tests
pytest lambda/tests/integration/ -v

# Run with coverage
pytest --cov=lambda --cov-report=html

# Run specific test
pytest lambda/tests/unit/test_city_repository.py::test_get_by_id -v

# Run with output
pytest -s lambda/tests/unit/test_city_repository.py
```

### 3. Code Quality

```bash
# Format code with black
black lambda/

# Sort imports
isort lambda/

# Lint with flake8
flake8 lambda/ --max-line-length=120

# Type checking with mypy (opcional)
mypy lambda/

# Run all quality checks
./scripts/code_quality.sh
```

**Criar script de qualidade:**

```bash
#!/bin/bash
# scripts/code_quality.sh

set -e

echo "Running code quality checks..."

# Format
echo "Formatting with black..."
black lambda/ --check

# Imports
echo "Checking imports with isort..."
isort lambda/ --check-only

# Lint
echo "Linting with flake8..."
flake8 lambda/ --max-line-length=120 --exclude=.venv

echo "Code quality checks passed! ✅"
```

---

## Testing Workflow

### Local Testing

```bash
# Run all tests
pytest

# Run with markers
pytest -m "not slow"  # Skip slow tests
pytest -m integration  # Only integration tests

# Run with verbose
pytest -v

# Run with coverage
pytest --cov=lambda --cov-report=term-missing

# Run performance tests
python scripts/performance_test_100_cities.py
```

### Manual Testing (Lambda Local)

```bash
# Install SAM CLI
pip install aws-sam-cli

# Invoke Lambda locally
sam local invoke WeatherForecastFunction \
  --event events/get_neighbors.json \
  --env-vars env.json

# Start API locally
sam local start-api \
  --env-vars env.json \
  --port 3000

# Test endpoint
curl http://localhost:3000/api/cities/neighbors/3543204?radius=50
```

**Event file example:**

```json
// events/get_neighbors.json
{
  "httpMethod": "GET",
  "path": "/api/cities/neighbors/3543204",
  "pathParameters": {
    "city_id": "3543204"
  },
  "queryStringParameters": {
    "radius": "50"
  },
  "headers": {}
}
```

---

## Deployment Workflow

### 1. Terraform Deployment

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan changes
terraform plan -var-file=terraform.tfvars

# Apply changes
terraform apply -var-file=terraform.tfvars

# Verificar deployment
aws lambda get-function --function-name weather-forecast-lambda-prod

# Verificar API Gateway
aws apigatewayv2 get-apis | jq '.Items[] | select(.Name=="weather-forecast-api-prod")'
```

### 2. Deploy Script

```bash
#!/bin/bash
# scripts/deploy-main.sh

set -e

ENVIRONMENT=${1:-prod}

echo "Deploying to $ENVIRONMENT..."

# 1. Build Lambda package
echo "Building Lambda package..."
cd lambda
pip install -r requirements.txt -t build/package/
cp -r application build/package/
cp -r domain build/package/
cp -r infrastructure build/package/
cp -r shared build/package/
cp config.py build/package/
cp lambda_function.py build/package/

# 2. Create deployment package
echo "Creating deployment package..."
cd build/package
zip -r ../../lambda_deployment.zip .
cd ../..

# 3. Deploy with Terraform
echo "Deploying with Terraform..."
cd ../terraform
terraform init
terraform apply -var="environment=$ENVIRONMENT" -auto-approve

echo "Deployment completed! ✅"

# 4. Verify deployment
FUNCTION_NAME="weather-forecast-lambda-$ENVIRONMENT"
aws lambda get-function --function-name $FUNCTION_NAME

# 5. Get API endpoint
API_ID=$(terraform output -raw api_gateway_id)
API_ENDPOINT="https://${API_ID}.execute-api.sa-east-1.amazonaws.com/prod"

echo "API Endpoint: $API_ENDPOINT"
echo "Test with: curl $API_ENDPOINT/api/cities/neighbors/3543204"
```

**Run:**

```bash
chmod +x scripts/deploy-main.sh
./scripts/deploy-main.sh prod
```

### 3. Rollback

```bash
# Rollback to previous Terraform state
cd terraform
terraform state pull > backup.tfstate
terraform apply -var-file=terraform.tfvars

# Rollback Lambda function
aws lambda update-function-code \
  --function-name weather-forecast-lambda-prod \
  --s3-bucket my-bucket \
  --s3-key lambda/previous-version.zip

# Rollback to specific version
aws lambda update-function-configuration \
  --function-name weather-forecast-lambda-prod \
  --revision-id previous-revision-id
```

---

## Git Workflow

### Branch Strategy (Git Flow)

```
main (produção)
  └─ develop (staging)
      ├─ feature/add-endpoint
      ├─ feature/improve-cache
      ├─ bugfix/fix-validation
      └─ hotfix/critical-bug
```

### Commit Messages

**Format:** `<type>(<scope>): <subject>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Add/update tests
- `chore`: Maintenance
- `perf`: Performance improvement

**Examples:**

```bash
git commit -m "feat(api): add new endpoint for regional weather"
git commit -m "fix(cache): handle TTL expiration correctly"
git commit -m "docs(readme): update deployment instructions"
git commit -m "refactor(use-cases): extract common logic to utility"
git commit -m "test(integration): add tests for weather endpoint"
git commit -m "perf(async): optimize concurrent requests with semaphore"
```

### Pull Request Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes and commit
git add .
git commit -m "feat: implement my feature"

# 3. Push to remote
git push origin feature/my-feature

# 4. Create PR via GitHub
gh pr create \
  --title "Add my feature" \
  --body "Description of changes" \
  --base develop

# 5. Address review comments
git add .
git commit -m "fix: address review comments"
git push

# 6. Merge PR (via GitHub UI or CLI)
gh pr merge --squash

# 7. Delete branch
git branch -d feature/my-feature
git push origin --delete feature/my-feature
```

---

## Monitoring & Debugging

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/weather-forecast-lambda-prod --follow

# Filter logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/weather-forecast-lambda-prod \
  --filter-pattern "ERROR"

# CloudWatch Insights query
aws logs start-query \
  --log-group-name /aws/lambda/weather-forecast-lambda-prod \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, message | filter message like /Cache hit/ | stats count() by bin(5m)'
```

### X-Ray Tracing

```bash
# Enable X-Ray tracing (Terraform)
resource "aws_lambda_function" "weather_forecast" {
  tracing_config {
    mode = "Active"
  }
}

# View traces
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)
```

### Debugging Locally

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use debugger
import pdb; pdb.set_trace()

# Or use ipdb
import ipdb; ipdb.set_trace()

# Print debug info
print(f"DEBUG: city_id={city_id}, radius={radius}")
```

---

## Performance Optimization

### Profiling

```python
# Profile code with cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### Memory Profiling

```python
# Install memory_profiler
pip install memory-profiler

# Profile function
from memory_profiler import profile

@profile
def my_function():
    # Your code
    pass

# Run
python -m memory_profiler script.py
```

### Lambda Optimization

```bash
# Increase memory (increases CPU proportionally)
aws lambda update-function-configuration \
  --function-name weather-forecast-lambda-prod \
  --memory-size 1024

# Configure reserved concurrency
aws lambda put-function-concurrency \
  --function-name weather-forecast-lambda-prod \
  --reserved-concurrent-executions 50

# Configure provisioned concurrency (keep warm)
aws lambda put-provisioned-concurrency-config \
  --function-name weather-forecast-lambda-prod \
  --provisioned-concurrent-executions 5 \
  --qualifier LATEST
```

---

## Troubleshooting

### Common Issues

**1. Import errors**

```bash
# Problem: ModuleNotFoundError

# Solution: Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/lambda"

# Or install as editable package
pip install -e .
```

**2. AWS permissions**

```bash
# Problem: Access denied

# Solution: Attach policy to IAM role
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaBasicExecutionRole
```

**3. Timeout errors**

```bash
# Problem: Lambda timeout (3s default)

# Solution: Increase timeout
aws lambda update-function-configuration \
  --function-name weather-forecast-lambda-prod \
  --timeout 30
```

**4. Memory errors**

```bash
# Problem: Out of memory

# Solution: Increase Lambda memory
aws lambda update-function-configuration \
  --function-name weather-forecast-lambda-prod \
  --memory-size 512
```

**5. Event loop errors**

```python
# Problem: RuntimeError: Event loop is closed

# Solution: Use asyncio.run()
def lambda_handler(event, context):
    async def execute_async():
        return await async_function()
    
    return asyncio.run(execute_async())
```

---

## Documentation

### Update Documentation

```bash
# Update docs
vim docs/api/ROUTES.md

# Generate README
# (If using auto-generated docs)
python scripts/generate_readme.py

# Commit docs
git add docs/
git commit -m "docs: update API documentation"
```

### Documentation Structure

```
docs/
├── architecture/           # Architecture documentation
│   └── CLEAN_ARCHITECTURE_DETAILED.md
├── api/                   # API documentation
│   └── ROUTES.md
├── infrastructure/        # Infrastructure documentation
│   ├── ASYNC_OPERATIONS.md
│   ├── DYNAMODB_CACHE.md
│   └── OPENWEATHER_INTEGRATION.md
└── development/           # Development guides
    ├── TESTING.md
    └── WORKFLOW.md
```

---

## Best Practices

### ✅ DO

1. **Always write tests first (TDD)**
   ```python
   # 1. Write test
   def test_new_feature():
       assert new_feature() == expected
   
   # 2. Implement feature
   def new_feature():
       return expected
   ```

2. **Use virtual environments**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Pin dependencies**
   ```
   # requirements.txt
   boto3==1.35.75
   aws-lambda-powertools==3.2.3
   ```

4. **Use environment variables**
   ```python
   API_KEY = os.getenv('OPENWEATHER_API_KEY')
   ```

5. **Follow Clean Architecture**
   ```
   Domain → Application → Infrastructure → Presentation
   ```

### ❌ DON'T

1. **❌ Don't commit secrets**
   ```bash
   # .gitignore
   .env
   *.tfvars
   secrets.json
   ```

2. **❌ Don't deploy untested code**
   ```bash
   # Always run tests before deploy
   pytest && ./scripts/deploy-main.sh
   ```

3. **❌ Don't hardcode values**
   ```python
   # ❌ ERRADO
   API_KEY = "1234567890"
   
   # ✅ CORRETO
   API_KEY = os.getenv('OPENWEATHER_API_KEY')
   ```

4. **❌ Don't skip code review**
   ```bash
   # Always create PR for review
   gh pr create
   ```

---

## Useful Commands

```bash
# Format code
black lambda/ && isort lambda/

# Run tests
pytest -v

# Deploy
./scripts/deploy-main.sh prod

# View logs
aws logs tail /aws/lambda/weather-forecast-lambda-prod --follow

# Invoke Lambda
aws lambda invoke \
  --function-name weather-forecast-lambda-prod \
  --payload '{"httpMethod":"GET","path":"/api/cities/neighbors/3543204"}' \
  response.json

# Check API health
curl https://your-api.execute-api.sa-east-1.amazonaws.com/prod/api/cities/neighbors/3543204

# Performance test
python scripts/performance_test_100_cities.py

# Git cleanup
git branch --merged | grep -v "\*" | xargs -n 1 git branch -d
```

---

## References

- **Python Best Practices:** https://docs.python-guide.org/
- **AWS Lambda Developer Guide:** https://docs.aws.amazon.com/lambda/
- **Terraform AWS Provider:** https://registry.terraform.io/providers/hashicorp/aws/
- **Clean Architecture:** https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- **Git Flow:** https://nvie.com/posts/a-successful-git-branching-model/
