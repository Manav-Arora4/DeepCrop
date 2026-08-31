"""
Database Seed Script: Populates initial sample records for demo testing.
"""

import asyncio
from datetime import datetime, timezone
from backend.core.database import get_session_factory, init_db
from backend.models.crop import CropModule
from backend.models.plant import Plant
from backend.models.device import Device
from backend.models.sensor_reading import SensorReading


async def seed():
    print("[Seed] Initializing database schema...")
    await init_db()

    factory = get_session_factory()
    async with factory() as session:
        # 1. Register Crop
        tomato = CropModule(
            id="tomato",
            name="Tomato",
            version="1.0.0",
            description="Solanum lycopersicum module with disease detection and advisory.",
            installed=True,
            module_path="crops/tomato",
            extra_metadata={},
        )
        session.add(tomato)

        # 2. Register Plant
        plant = Plant(
            id="plant_01",
            crop_id="tomato",
            name="Greenhouse Research Plot Alpha",
            location="Zone A, Row 3",
            growth_stage="flowering",
        )
        session.add(plant)

        # 3. Register Device
        dev = Device(
            id="esp32_001",
            plant_id="plant_01",
            crop_id="tomato",
            status="online",
            simulated=False,
            last_seen=datetime.now(timezone.utc),
        )
        session.add(dev)

        # 4. Insert initial sensor reading
        reading = SensorReading(
            device_id="esp32_001",
            crop_id="tomato",
            plant_id="plant_01",
            moisture=48.2,
            ph=6.4,
            temperature=24.5,
            humidity=62.0,
            data_source="simulated",
            is_valid=True,
            validation_notes="Seed telemetry data",
            timestamp=datetime.now(timezone.utc),
        )
        session.add(reading)

        await session.commit()
        print("[Seed] Successfully seeded initial crop, plant, device, and telemetry data!")


if __name__ == "__main__":
    asyncio.run(seed())
