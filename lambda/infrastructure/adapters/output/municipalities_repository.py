"""
Output Adapter: Implementação do Repositório de Cidades
Usa o municipalities_db.json como fonte de dados
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from domain.entities.city import City
from application.ports.output.city_repository_port import ICityRepository


class MunicipalitiesRepository(ICityRepository):
    """Repositório de municípios em memória com índices"""
    
    def __init__(self, json_path: str = None):
        """
        Inicializa o repositório
        
        Args:
            json_path: Caminho para o arquivo JSON com municípios.
                      Se None, usa o caminho padrão relativo a este arquivo.
        """
        self._data: Optional[List[Dict]] = None
        self._index_by_id: Optional[Dict[str, Dict]] = None
        self._index_by_state: Optional[Dict[str, List[Dict]]] = None
        
        # Se json_path não fornecido, usar caminho relativo ao diretório lambda/
        if json_path is None:
            # Obtém o diretório do arquivo atual (infrastructure/adapters/output/)
            current_file = Path(__file__)
            # Sobe até lambda/ e desce para data/
            lambda_dir = current_file.parent.parent.parent.parent
            json_path = lambda_dir / 'data' / 'municipalities_db.json'
        
        self.json_path = str(json_path)
        
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
    
    def _dict_to_entity(self, data: Dict) -> City:
        """Converte dict para entidade City"""
        return City(
            id=data['id'],
            name=data['name'],
            state=data['state'],
            region=data['region'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
    
    def get_by_id(self, city_id: str) -> Optional[City]:
        """Busca município por ID (O(1))"""
        data = self._index_by_id.get(city_id)
        return self._dict_to_entity(data) if data else None
    
    def get_by_state(self, state: str) -> List[City]:
        """Busca todos os municípios de um estado (O(1))"""
        data_list = self._index_by_state.get(state.upper(), [])
        return [self._dict_to_entity(data) for data in data_list]
    
    def search_by_name(self, name: str, state: Optional[str] = None) -> Optional[City]:
        """Busca município por nome (case-insensitive)"""
        name_lower = name.lower()
        
        # Se estado fornecido, buscar apenas nesse estado
        if state:
            municipalities = self._index_by_state.get(state.upper(), [])
        else:
            municipalities = self._data
        
        for m in municipalities:
            if m['name'].lower() == name_lower:
                return self._dict_to_entity(m)
        
        return None
    
    def get_all(self) -> List[City]:
        """Retorna todos os municípios"""
        return [self._dict_to_entity(data) for data in self._data]
    
    def get_with_coordinates(self) -> List[City]:
        """Retorna apenas municípios com coordenadas"""
        return [
            self._dict_to_entity(data)
            for data in self._data
            if data.get('latitude') and data.get('longitude')
        ]


# Singleton global - carregado uma vez e reutilizado entre invocações Lambda
_repository_instance = None


def get_repository(json_path: str = None) -> MunicipalitiesRepository:
    """
    Retorna instância singleton do repositório
    
    Em Lambda, a variável global persiste entre warm starts,
    evitando recarregar o JSON a cada invocação.
    
    Args:
        json_path: Caminho customizado para o JSON. Se None, usa o caminho padrão.
    """
    global _repository_instance
    
    if _repository_instance is None:
        _repository_instance = MunicipalitiesRepository(json_path)
    
    return _repository_instance
