import io
import pytest
from PIL import Image


@pytest.mark.asyncio
async def test_health_endpoint(client):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_crops_endpoints(client):
    res = await client.get("/crops")
    assert res.status_code == 200
    crops = res.json()
    assert len(crops) >= 2

    res_t = await client.get("/crops/tomato")
    assert res_t.status_code == 200
    tomato = res_t.json()
    assert tomato["name"] == "Tomato"
    assert "thresholds" in tomato


@pytest.mark.asyncio
async def test_sensor_ingestion_and_simulation(client):
    # Ingest manual reading
    reading_payload = {
        "device_id": "esp32_test",
        "crop_id": "tomato",
        "plant_id": "plant_01",
        "moisture": 45.5,
        "ph": 6.3,
        "temperature": 24.0,
        "humidity": 65.0,
        "data_source": "real",
    }
    res = await client.post("/sensors/reading", json=reading_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["moisture"] == 45.5
    assert body["threshold_status"]["moisture"]["status"] == "OPTIMAL"

    # Fetch latest
    res_latest = await client.get("/sensors/latest?plant_id=plant_01&crop_id=tomato")
    assert res_latest.status_code == 200

    # Simulate
    sim_res = await client.post("/sensors/simulate", json={
        "crop_id": "tomato",
        "plant_id": "plant_01",
        "scenario": "optimal",
        "count": 2,
    })
    assert sim_res.status_code == 200
    assert len(sim_res.json()) == 2


@pytest.mark.asyncio
async def test_cv_predict_endpoint(client):
    # Create small test RGB image in-memory
    img = Image.new("RGB", (224, 224), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("leaf.jpg", buf, "image/jpeg")}
    data = {"crop_id": "tomato", "plant_id": "plant_01"}

    res = await client.post("/cv/predict", files=files, data=data)
    assert res.status_code == 200
    pred = res.json()
    assert "disease" in pred
    assert pred["model_status"] in ["ready", "demo"]
    assert 0.0 <= pred["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_disease_risk_endpoint(client):
    res = await client.post("/disease-risk/predict", json={
        "crop_id": "tomato",
        "plant_id": "plant_01",
    })
    assert res.status_code == 200
    risk = res.json()
    assert "risk_score" in risk
    assert "risk_level" in risk
    assert isinstance(risk["contributing_factors"], list)
