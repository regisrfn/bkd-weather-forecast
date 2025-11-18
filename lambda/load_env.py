#!/usr/bin/env python3
"""
Script Python para carregar variáveis de ambiente do .env
Uso: python load_env.py [comando]
Exemplo: python load_env.py python test_lambda.py
"""
import os
import sys
from pathlib import Path
import subprocess


def load_env_file(env_path: Path) -> dict:
    """Carrega variáveis do arquivo .env"""
    env_vars = {}
    
    if not env_path.exists():
        print(f"❌ Arquivo {env_path} não encontrado!")
        return env_vars
    
    print(f"🔄 Carregando variáveis de {env_path}...")
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Ignorar comentários e linhas vazias
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                env_vars[key] = value
                
                # Mostrar confirmação (ocultando valores sensíveis)
                if 'KEY' in key or 'SECRET' in key or 'PASSWORD' in key:
                    print(f"  ✅ {key}=***{value[-4:]}")
                else:
                    print(f"  ✅ {key}={value}")
    
    return env_vars


def main():
    # Procurar .env no diretório pai
    env_path = Path(__file__).parent.parent / '.env'
    
    # Carregar variáveis
    env_vars = load_env_file(env_path)
    
    if not env_vars:
        sys.exit(1)
    
    # Se houver comando para executar, executar com as variáveis
    if len(sys.argv) > 1:
        print(f"\n🚀 Executando: {' '.join(sys.argv[1:])}\n")
        
        # Combinar variáveis atuais com as do .env
        env = os.environ.copy()
        env.update(env_vars)
        
        # Executar comando
        result = subprocess.run(sys.argv[1:], env=env)
        sys.exit(result.returncode)
    else:
        # Apenas mostrar as variáveis carregadas
        print(f"\n✅ {len(env_vars)} variáveis carregadas!")
        print("\n💡 Para usar, execute:")
        print(f"   python load_env.py python seu_script.py")


if __name__ == '__main__':
    main()
