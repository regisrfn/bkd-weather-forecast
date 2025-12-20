import pytest

from infrastructure.adapters.output.providers.ibge.ibge_geo_provider import IbgeGeoProvider


class FakeCache:
    def __init__(self, data=None):
        self.data = data or {}
        self.batch_set_calls = []

    def is_enabled(self):
        return True

    async def batch_get(self, keys):
        return {k: self.data[k] for k in keys if k in self.data}

    async def batch_set(self, items, ttl_seconds=None):
        self.data.update(items)
        self.batch_set_calls.append((items, ttl_seconds))
        return {k: True for k in items}


@pytest.mark.asyncio
async def test_batch_uses_cache_hits_only(monkeypatch):
    cached_mesh = {"type": "Feature", "id": "x"}
    cache_key = "ibge_mesh_123"
    fake_cache = FakeCache({cache_key: cached_mesh})
    provider = IbgeGeoProvider(cache=fake_cache)

    # Forçar falha se tentar buscar da API
    async def fail_fetch(_):
        raise AssertionError("Should not fetch from API when cache hits cover all")

    monkeypatch.setattr(provider, "_fetch_mesh_from_api", fail_fetch)

    result = await provider.get_municipality_meshes(["123", "123"])

    assert result == {"123": cached_mesh}
    assert fake_cache.batch_set_calls == []


@pytest.mark.asyncio
async def test_batch_fetches_missing_and_writes_cache(monkeypatch):
    fake_cache = FakeCache()
    provider = IbgeGeoProvider(cache=fake_cache)

    async def fake_fetch(city_id):
        return {"type": "Feature", "id": city_id}

    monkeypatch.setattr(provider, "_fetch_mesh_from_api", fake_fetch)

    result = await provider.get_municipality_meshes(["111", "222"])

    assert result == {
        "111": {"type": "Feature", "id": "111"},
        "222": {"type": "Feature", "id": "222"},
    }

    # Deve ter gravado em batch com prefixo
    assert len(fake_cache.batch_set_calls) == 1
    items, ttl = fake_cache.batch_set_calls[0]
    assert ttl is not None
    assert set(items.keys()) == {"ibge_mesh_111", "ibge_mesh_222"}


@pytest.mark.asyncio
async def test_batch_empty_ids_returns_empty(monkeypatch):
    fake_cache = FakeCache()
    provider = IbgeGeoProvider(cache=fake_cache)

    result = await provider.get_municipality_meshes([])

    assert result == {}
    assert fake_cache.batch_set_calls == []
