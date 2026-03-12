from httpx import AsyncClient


async def test_create_project(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "Test Project"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "draft"
    assert data["id"]


async def test_list_projects(client: AsyncClient) -> None:
    await client.post("/api/projects", json={"name": "P1"})
    await client.post("/api/projects", json={"name": "P2"})
    r = await client.get("/api/projects")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_get_project(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "Test"})
    pid = r.json()["id"]
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Test"


async def test_get_project_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/projects/nonexistent")
    assert r.status_code == 404


async def test_update_project(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "Old"})
    pid = r.json()["id"]
    r = await client.put(f"/api/projects/{pid}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


async def test_delete_project(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "ToDelete"})
    pid = r.json()["id"]
    r = await client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 404


async def test_create_shot(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/shots", json={"name": "S1", "prompt": "a cat"})
    assert r.status_code == 201
    assert r.json()["order_index"] == 0
    r = await client.post(f"/api/projects/{pid}/shots", json={"name": "S2"})
    assert r.json()["order_index"] == 1


async def test_reorder_shots(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    r1 = await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
    r2 = await client.post(f"/api/projects/{pid}/shots", json={"name": "S2"})
    sid1, sid2 = r1.json()["id"], r2.json()["id"]

    r = await client.put(
        f"/api/projects/{pid}/shots/reorder", json={"shot_ids": [sid2, sid1]}
    )
    assert r.status_code == 200
    assert r.json()[0]["id"] == sid2
    assert r.json()[0]["order_index"] == 0


async def test_update_shot(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
    sid = r.json()["id"]
    r = await client.put(f"/api/projects/{pid}/shots/{sid}", json={"prompt": "new prompt"})
    assert r.status_code == 200
    assert r.json()["prompt"] == "new prompt"


async def test_delete_shot(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
    sid = r.json()["id"]
    r = await client.delete(f"/api/projects/{pid}/shots/{sid}")
    assert r.status_code == 204


async def test_delete_project_cascades(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
    r = await client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
