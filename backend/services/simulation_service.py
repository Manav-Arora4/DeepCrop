import random
from typing import List, Dict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.sensor_reading import SensorReading
from backend.schemas.sensor import SimulationRequest, SensorReadingResponse
from backend.services.sensor_service import SensorService
from backend.services.crop_manager import CropManager


class SimulationService:
    """Generates realistic simulated sensor streams across 5 test scenarios."""

    SCENARIOS = {
        "optimal": {"moisture": (55.0, 5.0), "ph": (6.4, 0.2), "temperature": (23.0, 2.0), "humidity": (58.0, 4.0)},
        "drought": {"moisture": (18.0, 4.0), "ph": (6.2, 0.3), "temperature": (33.0, 2.5), "humidity": (32.0, 4.0)},
        "overwatered": {"moisture": (84.0, 4.0), "ph": (5.8, 0.2), "temperature": (21.0, 2.0), "humidity": (82.0, 4.0)},
        "disease_risk": {"moisture": (65.0, 5.0), "ph": (5.4, 0.3), "temperature": (28.0, 2.0), "humidity": (88.0, 3.0)},
        "random": None,
    }

    def __init__(self, db: AsyncSession, crop_manager: CropManager):
        self.db = db
        self.crop_manager = crop_manager
        self.sensor_service = SensorService(db, crop_manager)

    def _sample(self, mean: float, std: float, low: float, high: float) -> float:
        val = random.gauss(mean, std)
        return round(float(max(low, min(high, val))), 2)

    async def generate(self, req: SimulationRequest) -> List[SensorReadingResponse]:
        thresholds = self.crop_manager.get_thresholds(req.crop_id) or {}
        scenario_params = self.SCENARIOS.get(req.scenario)
        results = []

        for _ in range(req.count):
            if scenario_params:
                m_mean, m_std = scenario_params["moisture"]
                p_mean, p_std = scenario_params["ph"]
                t_mean, t_std = scenario_params["temperature"]
                h_mean, h_std = scenario_params["humidity"]

                moisture = self._sample(m_mean, m_std, 0.0, 100.0)
                ph = self._sample(p_mean, p_std, 0.0, 14.0)
                temperature = self._sample(t_mean, t_std, -10.0, 60.0)
                humidity = self._sample(h_mean, h_std, 0.0, 100.0)
            else:
                moisture = round(random.uniform(10.0, 90.0), 2)
                ph = round(random.uniform(4.5, 8.5), 2)
                temperature = round(random.uniform(12.0, 38.0), 2)
                humidity = round(random.uniform(25.0, 95.0), 2)

            record = SensorReading(
                device_id="simulator_virtual",
                crop_id=req.crop_id,
                plant_id=req.plant_id,
                moisture=moisture,
                ph=ph,
                temperature=temperature,
                humidity=humidity,
                data_source="simulated",
                is_valid=True,
                validation_notes=f"Synthetic scenario: {req.scenario}",
                timestamp=datetime.now(timezone.utc),
            )

            self.db.add(record)
            await self.db.flush()
            results.append(self.sensor_service._to_response(record, thresholds))

        await self.db.commit()
        return results
