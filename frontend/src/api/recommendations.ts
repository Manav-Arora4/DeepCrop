import { apiClient } from './client'
import type { Recommendation, DiseaseRiskPrediction } from './types'

// These call the local LLM; the first run also loads the model and embeddings, so allow 3 minutes
const LLM_TIMEOUT = 180_000

export async function predictDiseaseRisk(data: {
  crop_id: string
  plant_id: string
  sensor_reading_id?: number
  cv_prediction_id?: number
}): Promise<DiseaseRiskPrediction> {
  const res = await apiClient.post<DiseaseRiskPrediction>('/disease-risk/predict', data, { timeout: LLM_TIMEOUT })
  return res.data
}

export async function getRiskHistory(plantId: string): Promise<DiseaseRiskPrediction[]> {
  const res = await apiClient.get<DiseaseRiskPrediction[]>(`/disease-risk/history/${plantId}`)
  return res.data
}

export async function generateRecommendation(data: {
  crop_id: string
  plant_id: string
  sensor_reading_id?: number
  cv_prediction_id?: number
  risk_prediction_id?: number
}): Promise<Recommendation> {
  const res = await apiClient.post<Recommendation>('/recommendations/generate', data, { timeout: LLM_TIMEOUT })
  return res.data
}

export async function getRecommendationHistory(plantId: string): Promise<Recommendation[]> {
  const res = await apiClient.get<Recommendation[]>(`/recommendations/${plantId}`)
  return res.data
}
