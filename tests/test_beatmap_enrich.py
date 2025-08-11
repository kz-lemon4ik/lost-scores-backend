import asyncio
import pytest

from fastapi.testclient import TestClient

from app.models.beatmap import Beatmap
from app.models.invalid_md5 import InvalidMD5
from app.api.endpoints import beatmap as beatmap_endpoint


class MockResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockAsyncClient:
    def __init__(self, responses: list[MockResponse]):
        self._responses = responses
        self._index = 0

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url, headers):  # noqa: ANN001
        try:
            response = self._responses[self._index]
        except IndexError:
            raise AssertionError("Unexpected osu! API request") from None
        self._index += 1
        await asyncio.sleep(0)  # allow scheduling
        return response


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter = beatmap_endpoint.osu_api_rate_limiter
    limiter._timestamps.clear()  # type: ignore[attr-defined]
    yield
    limiter._timestamps.clear()  # type: ignore[attr-defined]


def test_enrich_returns_cached_data(db_session, client: TestClient, monkeypatch):
    md5 = "abc123"
    beatmap = Beatmap(
        beatmap_id=1,
        beatmapset_id=10,
        ranked_status="ranked",
        md5_hash=md5,
        artist="Artist",
        title="Title",
        creator="Creator",
        version="Hard",
        hit_objects=100,
        max_combo=800,
    )
    db_session.add(beatmap)
    db_session.commit()

    async def fail_fetch(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("osu! API should not be called for cached beatmaps")

    monkeypatch.setattr(beatmap_endpoint, "fetch_beatmap_by_md5", fail_fetch)

    async def fake_token() -> str:
        return "token"

    monkeypatch.setattr(beatmap_endpoint, "get_client_credentials_token", fake_token)

    response = client.post("/api/beatmaps/enrich", json={"md5_hashes": [md5]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["beatmaps"][md5]["title"] == "Title"


def test_enrich_fetches_and_saves_missing_map(db_session, client: TestClient, monkeypatch):
    md5 = "missing123"
    responses = [
        MockResponse(
            200,
            {
                "id": 999,
                "beatmapset_id": 555,
                "status": "ranked",
                "beatmapset": {
                    "artist": "Camellia",
                    "title": "Light Speed",
                    "creator": "Mapper",
                },
                "version": "Another",
                "count_circles": 10,
                "count_sliders": 20,
                "count_spinners": 1,
                "max_combo": 1234,
            },
        )
    ]

    monkeypatch.setattr(beatmap_endpoint.httpx, "AsyncClient", lambda *a, **k: MockAsyncClient(responses))

    async def fake_token() -> str:
        return "token"

    monkeypatch.setattr(beatmap_endpoint, "get_client_credentials_token", fake_token)

    response = client.post("/api/beatmaps/enrich", json={"md5_hashes": [md5]})
    assert response.status_code == 200
    payload = response.json()
    returned = payload["beatmaps"][md5]
    assert returned["creator"] == "Mapper"
    assert returned["hit_objects"] == 31

    stored = db_session.query(Beatmap).filter_by(md5_hash=md5).first()
    assert stored is not None
    assert stored.artist == "Camellia"
    assert stored.max_combo == 1234


def test_enrich_caches_invalid_md5(db_session, client: TestClient, monkeypatch):
    md5 = "invalid123"
    responses = [MockResponse(404, {})]

    monkeypatch.setattr(beatmap_endpoint.httpx, "AsyncClient", lambda *a, **k: MockAsyncClient(responses))

    async def fake_token() -> str:
        return "token"

    monkeypatch.setattr(beatmap_endpoint, "get_client_credentials_token", fake_token)

    response = client.post("/api/beatmaps/enrich", json={"md5_hashes": [md5]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["beatmaps"][md5] is None

    cached_invalid = db_session.query(InvalidMD5).filter_by(md5_hash=md5).first()
    assert cached_invalid is not None
