from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.sensor_reading import SensorReading
from backend.models.image_prediction import ImagePrediction
from backend.models.disease_risk_prediction import DiseaseRiskPrediction
from backend.models.recommendation import Recommendation
from backend.schemas.recommendation import RecommendationRequest, RecommendationResponse
from backend.services.crop_manager import CropManager
from backend.services.llm_service import LLMService
from backend.services.rag_service import get_rag_service
from backend.core.config import get_settings


SYSTEM_PROMPT = """You are an expert agricultural advisor and plant pathologist providing grounded, cautious, and practical recommendations to farmers and researchers.

Rules:
1. Ground your advice ONLY on the facts, sensor values, image analysis, and agronomic knowledge provided.
2. NEVER invent sensor readings, disease diagnoses, or agricultural facts not present in the context.
3. If evidence is ambiguous or confidence is low, clearly advise physical inspection or consulting a local agricultural extension specialist.
4. Structure your response into clear numbered sections:
   - Situation Summary (2-3 sentences)
   - Immediate Recommended Actions (numbered list)
   - Preventive & Cultural Measures for the next 7 days
   - Ongoing Monitoring Advice
"""


class RecommendationService:
    def __init__(self, db: AsyncSession, crop_manager: CropManager):
        self.db = db
        self.crop_manager = crop_manager
        self.llm_service = LLMService()
        self.rag_service = get_rag_service()
        self.settings = get_settings()

    async def generate(self, req: RecommendationRequest) -> RecommendationResponse:
        crop_data = self.crop_manager.get_crop(req.crop_id)
        crop_name = crop_data["name"] if crop_data else req.crop_id.title()
        thresholds = self.crop_manager.get_thresholds(req.crop_id) or {}

        # 1. Fetch sensor context
        sensor_text = "No recent sensor reading attached."
        sensor_obj = None
        if req.sensor_reading_id:
            s_res = await self.db.execute(
                select(SensorReading).where(SensorReading.id == req.sensor_reading_id)
            )
            sensor_obj = s_res.scalar_one_or_none()
            if sensor_obj:
                sensor_text = (
                    f"Soil Moisture: {sensor_obj.moisture}% | Soil pH: {sensor_obj.ph} | "
                    f"Temperature: {sensor_obj.temperature}°C | Humidity: {sensor_obj.humidity}% "
                    f"(Data source: {sensor_obj.data_source})"
                )

        # 2. Fetch CV context
        cv_text = "No leaf imagery prediction attached."
        cv_obj = None
        disease_query = ""
        if req.cv_prediction_id:
            cv_res = await self.db.execute(
                select(ImagePrediction).where(ImagePrediction.id == req.cv_prediction_id)
            )
            cv_obj = cv_res.scalar_one_or_none()
            if cv_obj:
                cv_text = (
                    f"Disease Detected: {cv_obj.disease} ({cv_obj.confidence:.1%} confidence) "
                    f"[Model status: {cv_obj.model_status}]"
                )
                if cv_obj.low_confidence_warning:
                    cv_text += " (⚠️ Low confidence warning flagged)"
                disease_query = cv_obj.disease

        # 3. Fetch Risk context
        risk_text = "No multimodal disease-risk assessment attached."
        urgency = "medium"
        risk_obj = None
        if req.risk_prediction_id:
            r_res = await self.db.execute(
                select(DiseaseRiskPrediction).where(DiseaseRiskPrediction.id == req.risk_prediction_id)
            )
            risk_obj = r_res.scalar_one_or_none()
            if risk_obj:
                risk_text = (
                    f"Calculated Risk Score: {risk_obj.risk_score:.0%} ({risk_obj.risk_level.upper()}) | "
                    f"Factors: {', '.join(risk_obj.contributing_factors)}"
                )
                urgency = risk_obj.risk_level

        # 4. Query RAG Knowledge Base
        rag_query = f"{crop_name} {disease_query} humidity temperature soil moisture management"
        retrieved = await self.rag_service.retrieve(req.crop_id, rag_query, k=3)
        knowledge_context = "\n\n".join([f"[{r['source']}]: {r['content']}" for r in retrieved])
        if not knowledge_context:
            knowledge_context = "General crop production standards apply."

        user_message = f"""Crop: {crop_name}
Plant ID: {req.plant_id}

Computer Vision Imagery:
{cv_text}

IoT Environmental Sensor Conditions:
{sensor_text}

Multimodal Disease Risk Assessment:
{risk_text}

Retrieved Agronomic Knowledge Base Documents:
{knowledge_context}

Please provide an evidence-based recommendation for the farmer.
"""

        # 5. Invoke LLM with fallback
        provider_info = self.llm_service.get_info()
        provider_name = provider_info["provider"]
        model_name = provider_info["model"]

        try:
            raw_text = await self.llm_service.generate_response(SYSTEM_PROMPT, user_message)
        except Exception as e:
            raw_text = (
                f"Agricultural Decision Support Notice (LLM Offline / Fallback):\n"
                f"Based on current observations for {crop_name} ({req.plant_id}):\n"
                f"1. Environmental Status: {sensor_text}\n"
                f"2. Visual Foliar Status: {cv_text}\n"
                f"3. Risk Level: {urgency.upper()}\n\n"
                f"Recommended immediate actions: Inspect plant visually, verify irrigation drippers, "
                f"and ensure optimal airflow. If fungal symptoms persist, apply protective copper or biofungicide."
            )

        # Parse actions
        lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
        actions = [ln for ln in lines if ln.startswith(("1.", "2.", "3.", "4.", "-", "•"))]
        if not actions:
            actions = ["Inspect foliar canopy", "Maintain soil moisture in 40-70% range", "Monitor relative humidity"]

        sources_metadata = [
            {"title": r.get("source", "Doc"), "topic": "agronomy", "relevance": r.get("relevance", 0.8)}
            for r in retrieved
        ]

        record = Recommendation(
            plant_id=req.plant_id,
            crop_id=req.crop_id,
            sensor_reading_id=req.sensor_reading_id,
            cv_prediction_id=req.cv_prediction_id,
            risk_prediction_id=req.risk_prediction_id,
            summary=raw_text[:300] + "...",
            contributing_factors=risk_obj.contributing_factors if risk_obj else ["Environmental observation"],
            recommended_actions=actions[:5],
            prevention_steps=["Regular weekly scouting", "Sanitize pruning tools", "Maintain optimal irrigation"],
            monitoring_advice=f"Check {crop_name} daily for changes in leaf spotting or moisture stress.",
            urgency=urgency,
            sources=sources_metadata,
            llm_provider=provider_name,
            llm_model=model_name,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        return RecommendationResponse(
            id=record.id,
            plant_id=record.plant_id,
            crop_id=record.crop_id,
            summary=raw_text,
            contributing_factors=record.contributing_factors,
            recommended_actions=record.recommended_actions,
            prevention_steps=record.prevention_steps,
            monitoring_advice=record.monitoring_advice,
            urgency=record.urgency,
            sources=record.sources,
            llm_provider=record.llm_provider,
            llm_model=record.llm_model,
            timestamp=record.timestamp,
        )
