from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.models.sensor_reading import SensorReading
from backend.schemas.sensor import SensorReadingCreate, SensorReadingResponse, ThresholdValue
from backend.services.crop_manager import CropManager


class SensorService:
    def __init__(self, db: AsyncSession, crop_manager: CropManager):
        self.db = db
        self.crop_manager = crop_manager

    def validate_reading(self, reading: SensorReadingCreate) -> Tuple[bool, Optional[str]]:
        """Validate physical plausibility of environmental values."""
        notes = []
        if reading.moisture is not None and not (0.0 <= reading.moisture <= 100.0):
            notes.append("Moisture out of range [0, 100]")
        if reading.ph is not None and not (0.0 <= reading.ph <= 14.0):
            notes.append("pH out of range [0, 14]")
        if reading.temperature is not None and not (-50.0 <= reading.temperature <= 80.0):
            notes.append("Temperature out of range [-50, 80]")
        if reading.humidity is not None and not (0.0 <= reading.humidity <= 100.0):
            notes.append("Humidity out of range [0, 100]")

        if notes:
            return False, "; ".join(notes)
        return True, None

    def get_threshold_status(self, reading: SensorReading, thresholds: Dict) -> Dict[str, ThresholdValue]:
        """Compute LOW, OPTIMAL, HIGH status for each parameter against crop thresholds."""
        res = {}
        fields = [
            ("moisture", reading.moisture),
            ("ph", reading.ph),
            ("temperature", reading.temperature),
            ("humidity", reading.humidity),
        ]

        for param, val in fields:
            t = thresholds.get(param, {})
            unit = t.get("unit", "")
            if val is None:
                res[param] = ThresholdValue(value=None, status="UNKNOWN", unit=unit)
                continue

            low_max = t.get("low_max")
            opt_min = t.get("optimal_min")
            opt_max = t.get("optimal_max")
            high_min = t.get("high_min")

            if low_max is not None and val < low_max:
                status = "LOW"
            elif opt_min is not None and opt_max is not None and (opt_min <= val <= opt_max):
                status = "OPTIMAL"
            elif high_min is not None and val > high_min:
                status = "HIGH"
            else:
                status = "UNKNOWN"

            res[param] = ThresholdValue(value=val, status=status, unit=unit)

        return res

    def _to_response(self, reading: SensorReading, thresholds: Dict) -> SensorReadingResponse:
        t_status = self.get_threshold_status(reading, thresholds)
        return SensorReadingResponse(
            id=reading.id,
            device_id=reading.device_id,
            crop_id=reading.crop_id,
            plant_id=reading.plant_id,
            moisture=reading.moisture,
            ph=reading.ph,
            temperature=reading.temperature,
            humidity=reading.humidity,
            data_source=reading.data_source,
            threshold_status=t_status,
            timestamp=reading.timestamp,
        )

    async def ingest_reading(self, reading_in: SensorReadingCreate) -> SensorReadingResponse:
        is_valid, notes = self.validate_reading(reading_in)
        thresholds = self.crop_manager.get_thresholds(reading_in.crop_id) or {}
        ts = reading_in.timestamp or datetime.now(timezone.utc)

        record = SensorReading(
            device_id=reading_in.device_id,
            crop_id=reading_in.crop_id,
            plant_id=reading_in.plant_id,
            moisture=reading_in.moisture,
            ph=reading_in.ph,
            temperature=reading_in.temperature,
            humidity=reading_in.humidity,
            data_source=reading_in.data_source,
            is_valid=is_valid,
            validation_notes=notes,
            timestamp=ts,
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        return self._to_response(record, thresholds)

    async def get_latest(self, plant_id: str, crop_id: str) -> Optional[SensorReadingResponse]:
        thresholds = self.crop_manager.get_thresholds(crop_id) or {}
        stmt = (
            select(SensorReading)
            .where(and_(SensorReading.plant_id == plant_id, SensorReading.crop_id == crop_id))
            .order_by(SensorReading.timestamp.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            return None
        return self._to_response(record, thresholds)

    async def get_history(self, plant_id: str, crop_id: str, range_code: str = "1d") -> List[SensorReadingResponse]:
        thresholds = self.crop_manager.get_thresholds(crop_id) or {}
        now = datetime.now(timezone.utc)
        deltas = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "1d": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        since = now - deltas.get(range_code, timedelta(days=1))

        stmt = (
            select(SensorReading)
            .where(and_(
                SensorReading.plant_id == plant_id,
                SensorReading.crop_id == crop_id,
                SensorReading.timestamp >= since,
            ))
            .order_by(SensorReading.timestamp.asc())
        )
        res = await self.db.execute(stmt)
        records = res.scalars().all()
        return [self._to_response(r, thresholds) for r in records]
