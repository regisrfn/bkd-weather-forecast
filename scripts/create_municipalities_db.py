"""
Script para buscar todos os municípios brasileiros do IBGE
e criar um banco de dados local em JSON

API IBGE Localidades: https://servicodados.ibge.gov.br/api/docs/localidades
"""
import requests
import json
from typing import List, Dict


def fetch_all_municipalities() -> List[Dict]:
    """
    Busca todos os municípios brasileiros do IBGE
    
    API: GET https://servicodados.ibge.gov.br/api/v1/localidades/municipios
    
    Returns:
        list: Lista com todos os municípios
    """
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    
    print("🌍 Buscando municípios do IBGE...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        municipalities = response.json()
        print(f"✅ {len(municipalities)} municípios encontrados")
        
        return municipalities
        
    except Exception as e:
        print(f"❌ Erro ao buscar municípios: {e}")
        return []


def parse_municipality_data(raw_data: List[Dict]) -> List[Dict]:
    """
    Parseia dados brutos do IBGE para formato simplificado
    
    Estrutura da resposta IBGE:
    {
      "id": 3543204,
      "nome": "Ribeirão do Sul",
      "microrregiao": {...},
      "regiao-imediata": {...}
    }
    
    Args:
        raw_data: Dados brutos do IBGE
    
    Returns:
        list: Municípios no formato simplificado
    """
    municipalities = []
    
    for mun in raw_data:
        # Extrair dados com fallback seguro
        try:
            # Tentar usar microrregiao primeiro
            if mun.get('microrregiao'):
                state_data = mun['microrregiao']['mesorregiao']['UF']
                microregion = mun['microrregiao']['nome']
                mesoregion = mun['microrregiao']['mesorregiao']['nome']
            # Fallback para regiao-imediata
            elif mun.get('regiao-imediata'):
                state_data = mun['regiao-imediata']['regiao-intermediaria']['UF']
                microregion = mun['regiao-imediata']['nome']
                mesoregion = mun['regiao-imediata']['regiao-intermediaria']['nome']
            else:
                continue
            
            municipality = {
                'id': str(mun['id']),
                'name': mun['nome'],
                'state': state_data['sigla'],
                'state_name': state_data['nome'],
                'microregion': microregion,
                'mesoregion': mesoregion,
                'region': state_data['regiao']['nome']
            }
            municipalities.append(municipality)
        except (KeyError, TypeError) as e:
            print(f"⚠️  Erro ao processar município {mun.get('nome', 'desconhecido')}: {e}")
            continue
    
    return municipalities


def fetch_municipality_coordinates(municipality_id: str) -> Dict:
    """
    Busca coordenadas geográficas de um município específico
    
    API: GET https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{id}
    
    Nota: A API do IBGE não retorna coordenadas diretamente.
    Alternativas:
    1. API de Geocodificação do IBGE (se disponível)
    2. Usar base de dados local com coordenadas
    3. Integrar com outras APIs (Nominatim, Google, etc.)
    
    Args:
        municipality_id: Código IBGE do município
    
    Returns:
        dict: Dados com coordenadas (se disponível)
    """
    # Por enquanto, retornar estrutura vazia
    # Em produção, integrar com API de geocodificação
    return {
        'latitude': None,
        'longitude': None
    }


def save_to_json(data: List[Dict], filename: str = 'municipalities_db.json'):
    """
    Salva dados em arquivo JSON
    
    Args:
        data: Lista de municípios
        filename: Nome do arquivo
    """
    print(f"\n💾 Salvando em {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(data)} municípios salvos com sucesso!")


def create_municipalities_database():
    """
    Cria banco de dados completo de municípios brasileiros
    """
    print("=" * 60)
    print("🗺️  CRIANDO BANCO DE DADOS DE MUNICÍPIOS")
    print("=" * 60)
    
    # 1. Buscar todos os municípios
    raw_municipalities = fetch_all_municipalities()
    
    if not raw_municipalities:
        print("❌ Não foi possível buscar os municípios")
        return
    
    # 2. Parsear dados
    print("\n📊 Parseando dados...")
    municipalities = parse_municipality_data(raw_municipalities)
    
    # 3. Estatísticas
    print("\n📈 Estatísticas:")
    states = {}
    for mun in municipalities:
        state = mun['state']
        states[state] = states.get(state, 0) + 1
    
    print(f"   Total de municípios: {len(municipalities)}")
    print(f"   Estados: {len(states)}")
    print(f"\n   Top 5 estados com mais municípios:")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   - {state}: {count} municípios")
    
    # 4. Salvar
    save_to_json(municipalities)
    
    # 5. Criar índice por estado
    print("\n📂 Criando índices por estado...")
    for state_code in states.keys():
        state_municipalities = [m for m in municipalities if m['state'] == state_code]
        save_to_json(state_municipalities, f'municipalities_{state_code}.json')
    
    print("\n" + "=" * 60)
    print("✅ Banco de dados criado com sucesso!")
    print("=" * 60)
    print("\nArquivos gerados:")
    print("  - municipalities_db.json (todos os municípios)")
    print("  - municipalities_{UF}.json (por estado)")


if __name__ == '__main__':
    create_municipalities_database()
