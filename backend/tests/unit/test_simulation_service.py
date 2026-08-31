import pytest
from backend.services.simulation_service import SimulationService
from backend.services.crop_manager import CropManager
from backend.schemas.sensor import SimulationRequest


@pytest.mark.asyncio
async def test_simulation_scenarios(test_db_session):
    manager = CropManager(crops_dir="./crops")
    sim_service = SimulationService(test_db_session, manager)

    req = SimulationRequest(
        crop_id="tomato",
        plant_id="plant_01",
        scenario="optimal",
        count=3,
    )
    readings = await sim_service.generate(req)
    assert len(readings) == 3
    for r in readings:
        assert r.data_source == "simulated"
        assert 0.0 <= r.moisture <= 100.0
        assert 0.0 <= r.ph <= 14.0
        assert "moisture" in r.threshold_status
