"""
Dados das cidades da região de Ribeirão do Sul
"""

CITIES_DATABASE = {
    '3543204': {
        'id': '3543204',
        'name': 'Ribeirão do Sul',
        'latitude': -22.7572,
        'longitude': -49.9439,
        'state': 'SP'
    },
    '3550506': {
        'id': '3550506',
        'name': 'São Pedro do Turvo',
        'latitude': -22.8978,
        'longitude': -49.7433,
        'state': 'SP'
    },
    '3545407': {
        'id': '3545407',
        'name': 'Salto Grande',
        'latitude': -22.8936,
        'longitude': -49.9853,
        'state': 'SP'
    },
    '3534708': {
        'id': '3534708',
        'name': 'Ourinhos',
        'latitude': -22.9789,
        'longitude': -49.8708,
        'state': 'SP'
    },
    '3510153': {
        'id': '3510153',
        'name': 'Canitar',
        'latitude': -23.0028,
        'longitude': -49.7817,
        'state': 'SP'
    },
    '3546405': {
        'id': '3546405',
        'name': 'Santa Cruz do Rio Pardo',
        'latitude': -22.8997,
        'longitude': -49.6336,
        'state': 'SP'
    },
    '3538808': {
        'id': '3538808',
        'name': 'Piraju',
        'latitude': -23.1933,
        'longitude': -49.3847,
        'state': 'SP'
    }
}


def get_city_by_id(city_id: str):
    """Retorna dados de uma cidade pelo ID do IBGE"""
    return CITIES_DATABASE.get(city_id)


def get_all_cities():
    """Retorna todas as cidades"""
    return list(CITIES_DATABASE.values())
