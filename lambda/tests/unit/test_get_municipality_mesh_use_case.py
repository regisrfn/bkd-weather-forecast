import pytest

from application.use_cases.get_municipality_mesh_use_case import GetMunicipalityMeshUseCase
from domain.entities.city import City
from domain.exceptions import CityNotFoundException, GeoDataNotFoundException


class FakeCityRepository:
    """Repositório fake para testes do use case"""

    def __init__(self, cities: dict[str, City]):
        self.cities = cities

    def get_by_id(self, city_id: str):
        return self.cities.get(city_id)


class FakeGeoProvider:
    """Provider fake para controlar retornos e exceções"""

    def __init__(self, mesh: dict, raise_not_found: bool = False):
        self.mesh = mesh
        self.raise_not_found = raise_not_found
        self.calls: list[str] = []

    @property
    def provider_name(self) -> str:
        return "FakeIBGE"

    async def get_municipality_mesh(self, city_id: str):
        self.calls.append(city_id)
        if self.raise_not_found:
            raise GeoDataNotFoundException("Geo data not found", details={"city_id": city_id})
        return self.mesh


@pytest.mark.asyncio
async def test_returns_mesh_when_city_exists():
    city = City(id="1234567", name="Test City", state="TS", region="S", latitude=0.0, longitude=0.0)
    repo = FakeCityRepository({"1234567": city})
    mesh = {"type": "Feature", "properties": {"id": "1234567"}}
    provider = FakeGeoProvider(mesh=mesh)

    use_case = GetMunicipalityMeshUseCase(city_repository=repo, geo_provider=provider)

    result = await use_case.execute("1234567")

    assert result == mesh
    assert provider.calls == ["1234567"]


@pytest.mark.asyncio
async def test_raises_when_city_not_found():
    repo = FakeCityRepository({})
    provider = FakeGeoProvider(mesh={})
    use_case = GetMunicipalityMeshUseCase(city_repository=repo, geo_provider=provider)

    with pytest.raises(CityNotFoundException):
        await use_case.execute("9999999")

    assert provider.calls == []


@pytest.mark.asyncio
async def test_propagates_geo_data_not_found():
    city = City(id="1111111", name="City", state="ST", region="S", latitude=0.0, longitude=0.0)
    repo = FakeCityRepository({"1111111": city})
    provider = FakeGeoProvider(mesh={}, raise_not_found=True)

    use_case = GetMunicipalityMeshUseCase(city_repository=repo, geo_provider=provider)

    with pytest.raises(GeoDataNotFoundException):
        await use_case.execute("1111111")

    assert provider.calls == ["1111111"]
