import pytest

from application.use_cases.get_municipality_meshes_use_case import GetMunicipalityMeshesUseCase
from domain.entities.city import City
from domain.exceptions import CityNotFoundException


class FakeCityRepository:
    def __init__(self, cities: dict[str, City]):
        self.cities = cities

    def get_by_id(self, city_id: str):
        return self.cities.get(city_id)


class FakeGeoProvider:
    def __init__(self, meshes: dict[str, dict]):
        self.meshes = meshes
        self.calls: list[list[str]] = []

    @property
    def provider_name(self) -> str:
        return "FakeIBGE"

    async def get_municipality_meshes(self, city_ids: list[str]):
        self.calls.append(city_ids)
        return {city_id: self.meshes[city_id] for city_id in city_ids if city_id in self.meshes}


def _make_city(city_id: str) -> City:
    return City(
        id=city_id,
        name=f"City {city_id}",
        state="ST",
        region="S",
        latitude=0.0,
        longitude=0.0
    )


@pytest.mark.asyncio
async def test_returns_meshes_for_multiple_cities():
    cities = {"111": _make_city("111"), "222": _make_city("222")}
    repo = FakeCityRepository(cities)
    meshes = {"111": {"type": "Feature"}, "222": {"type": "Feature"}}
    provider = FakeGeoProvider(meshes)

    use_case = GetMunicipalityMeshesUseCase(city_repository=repo, geo_provider=provider)

    result = await use_case.execute(["111", "222", "111"])  # inclui duplicada

    assert result == meshes
    # Provider deve ser chamado apenas com IDs únicos
    assert provider.calls == [["111", "222"]]


@pytest.mark.asyncio
async def test_raises_when_any_city_missing():
    repo = FakeCityRepository({"111": _make_city("111")})
    provider = FakeGeoProvider({})
    use_case = GetMunicipalityMeshesUseCase(city_repository=repo, geo_provider=provider)

    with pytest.raises(CityNotFoundException):
        await use_case.execute(["111", "222"])

    # Provider não deve ser chamado quando há cidade inexistente
    assert provider.calls == []


@pytest.mark.asyncio
async def test_returns_empty_dict_when_no_ids():
    repo = FakeCityRepository({})
    provider = FakeGeoProvider({})
    use_case = GetMunicipalityMeshesUseCase(city_repository=repo, geo_provider=provider)

    result = await use_case.execute([])

    assert result == {}
    assert provider.calls == []
