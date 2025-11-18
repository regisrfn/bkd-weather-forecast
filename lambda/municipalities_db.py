"""
Serviço de banco de dados de municípios brasileiros
Carrega dados do JSON e cria índices em memória para busca rápida
"""
import json
import os
from typing import Dict, List, Optional
from functools import lru_cache


class MunicipalitiesDB:
    """Banco de dados de municípios em memória com índices"""
    
    def __init__(self, json_path: str = 'data/municipalities_db.json'):
        """
        Inicializa o banco de dados
        
        Args:
            json_path: Caminho para o arquivo JSON com municípios
        """
        self._data = None
        self._index_by_id = None
        self._index_by_state = None
        self.json_path = json_path
        
        # Carregar dados na inicialização
        self._load_data()
    
    def _load_data(self):
        """Carrega dados do JSON e cria índices"""
        if self._data is not None:
            return  # Já carregado
        
        print(f"📂 Carregando banco de municípios de {self.json_path}...")
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)
        
        # Criar índices para busca rápida O(1)
        self._index_by_id = {m['id']: m for m in self._data}
        
        # Índice por estado
        self._index_by_state = {}
        for m in self._data:
            state = m['state']
            if state not in self._index_by_state:
                self._index_by_state[state] = []
            self._index_by_state[state].append(m)
        
        print(f"✅ {len(self._data)} municípios carregados")
        print(f"📊 {len(self._index_by_state)} estados indexados")
        print(f"💾 Municípios com coordenadas: {len([m for m in self._data if m.get('latitude')])}")
    
    def get_by_id(self, municipality_id: str) -> Optional[Dict]:
        """
        Busca município por ID (O(1))
        
        Args:
            municipality_id: Código IBGE do município
        
        Returns:
            dict: Dados do município ou None
        """
        return self._index_by_id.get(municipality_id)
    
    def get_by_state(self, state: str) -> List[Dict]:
        """
        Busca todos os municípios de um estado (O(1))
        
        Args:
            state: Sigla do estado (ex: SP, MG, RJ)
        
        Returns:
            list: Lista de municípios do estado
        """
        return self._index_by_state.get(state.upper(), [])
    
    def search_by_name(self, name: str, state: str = None) -> Optional[Dict]:
        """
        Busca município por nome (case-insensitive)
        
        Args:
            name: Nome do município
            state: Sigla do estado (opcional, ajuda a desambiguar)
        
        Returns:
            dict: Primeiro município encontrado ou None
        """
        name_lower = name.lower()
        
        # Se estado fornecido, buscar apenas nesse estado
        if state:
            municipalities = self.get_by_state(state)
        else:
            municipalities = self._data
        
        for m in municipalities:
            if m['name'].lower() == name_lower:
                return m
        
        return None
    
    def get_all(self) -> List[Dict]:
        """Retorna todos os municípios"""
        return self._data
    
    def get_with_coordinates(self) -> List[Dict]:
        """Retorna apenas municípios com coordenadas"""
        return [m for m in self._data if m.get('latitude') and m.get('longitude')]
    
    def count(self) -> int:
        """Retorna número total de municípios"""
        return len(self._data)
    
    def count_by_state(self, state: str) -> int:
        """Retorna número de municípios em um estado"""
        return len(self.get_by_state(state))


# Singleton global - carregado uma vez e reutilizado entre invocações Lambda
_db_instance = None


def get_db(json_path: str = 'data/municipalities_db.json') -> MunicipalitiesDB:
    """
    Retorna instância singleton do banco de dados
    
    Em Lambda, a variável global persiste entre warm starts,
    evitando recarregar o JSON a cada invocação.
    
    Args:
        json_path: Caminho para o arquivo JSON
    
    Returns:
        MunicipalitiesDB: Instância do banco de dados
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = MunicipalitiesDB(json_path)
    
    return _db_instance


if __name__ == '__main__':
    # Testes
    import sys
    
    # Usar caminho relativo ou absoluto correto
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        json_path = 'data/municipalities_db.json'
    
    db = get_db(json_path)
    
    print("\n" + "="*70)
    print("🧪 TESTES DO BANCO DE DADOS")
    print("="*70)
    
    # Teste 1: Busca por ID
    print("\n1️⃣  Busca por ID (São Paulo)")
    sp = db.get_by_id('3550308')
    if sp:
        print(f"   ✅ {sp['name']}/{sp['state']}")
        print(f"   📍 ({sp.get('latitude')}, {sp.get('longitude')})")
    
    # Teste 2: Busca por nome
    print("\n2️⃣  Busca por nome (Rio de Janeiro)")
    rj = db.search_by_name('Rio de Janeiro', 'RJ')
    if rj:
        print(f"   ✅ {rj['name']}/{rj['state']} - ID: {rj['id']}")
    
    # Teste 3: Busca por estado
    print("\n3️⃣  Municípios de SP")
    sp_cities = db.get_by_state('SP')
    print(f"   ✅ {len(sp_cities)} municípios encontrados")
    print(f"   Exemplos: {', '.join([c['name'] for c in sp_cities[:5]])}...")
    
    # Teste 4: Estatísticas
    print("\n4️⃣  Estatísticas")
    print(f"   Total de municípios: {db.count()}")
    print(f"   Com coordenadas: {len(db.get_with_coordinates())}")
    print(f"   Municípios em MG: {db.count_by_state('MG')}")
    
    # Teste 5: Performance
    print("\n5️⃣  Teste de performance")
    import time
    
    # Busca por ID (O(1))
    start = time.time()
    for _ in range(10000):
        db.get_by_id('3550308')
    elapsed = (time.time() - start) * 1000
    print(f"   10.000 buscas por ID: {elapsed:.2f}ms ({elapsed/10000:.4f}ms/busca)")
    
    # Busca por estado (O(1))
    start = time.time()
    for _ in range(1000):
        db.get_by_state('SP')
    elapsed = (time.time() - start) * 1000
    print(f"   1.000 buscas por estado: {elapsed:.2f}ms ({elapsed/1000:.4f}ms/busca)")
