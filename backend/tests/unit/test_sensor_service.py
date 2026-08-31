import pytest
from backend.services.sensor_service import SensorService
from backend.schemas.sensor import SensorReadingCreate
from backend.models.sensor_reading import SensorReading


@pytest.mark.asyncio
async def test_sensor_validation():
    service = SensorService(db=None, crop_manager=None)

    valid_reading = SensorReadingCreate(
        device_id="esp_01",
        crop_id="tomato",
        plant_id="plant_01",
        moisture=45.0,
        ph=6.5,
        temperature=25.0,
        humidity=60.0,
    )
    is_valid, notes = service.validate_reading(valid_reading)
    assert is_valid is True
    assert notes is None

    invalid_reading = SensorReadingCreate(
        device_id="esp_01",
        crop_id="tomato",
        plant_id="plant_01",
        moisture=120.0,  # Impossible
        ph=-1.0,        # Impossible
        temperature=150.0,
        humidity=150.0,
    )
    is_valid, notes = service.validate_reading(invalid_reading)
    assert is_valid is False
    assert "Moisture" in notes
    assert "pH" in notes


@pytest.mark.asyncio
async def test_threshold_evaluation():
    service = SensorService(db=None, crop_manager=None)

    thresholds = {
        "moisture": {"low_max": 30.0, "optimal_min": 30.0, "optimal_max": 70.0, "high_min": 70.0, "unit": "%"},
        "ph": {"low_max": 5.5, "optimal_min": 5.5, "optimal_max": 7.0, "high_min": 7.0, "unit": "pH"},
        "temperature": {"low_max": 10.0, "optimal_min": 10.0, "optimal_max": 30.0, "high_min": 30.0, "unit": "°C"},
        "humidity": {"low_max": 40.0, "optimal_min": 40.0, "optimal_max": 70.0, "high_min": 70.0, "unit": "%"},
    }

    reading = SensorReading(
        id=1,
        device_id="dev1",
        crop_id="tomato",
        plant_id="p1",
        moisture=20.0,      # LOW
        ph=6.2,             # OPTIMAL
        temperature=35.0,   # HIGH
        humidity=None,      # UNKNOWN
        data_source="real",
    )

    res = service.get_threshold_status(reading, thresholds)
    assert res["moisture"].status == "LOW"
    assert res["ph"].status == "OPTIMAL"
    assert res["temperature"].status == "HIGH"
    assert res["humidity"].status == "UNKNOWN"
