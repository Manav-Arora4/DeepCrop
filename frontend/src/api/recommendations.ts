import { apiClient } from './client'
import type { Recommendation, DiseaseRiskPrediction } from './types'

export async function predictDiseaseRisk(data: {
  crop_id: string
  plant_id: string
  sensor_reading_id?: number
  cv_prediction_id?: number
}): Promise<DiseaseRiskPrediction> {
  const res = await apiClient.post<DiseaseRiskPrediction>('/disease-risk/predict', data)
  return res.data
}

export async function generateRecommendation(data: {
  crop_id: string
  plant_id: string
  sensor_reading_id?: number
  cv_prediction_id?: number
  risk_prediction_id?: number
}): Promise<Recommendation> {
  const res = await apiClient.post<Recommendation>('/recommendations/generate', data)
  return res.data
}

export async function getRecommendationHistory(plantId: string): Promise<Recommendation[]> {
  const res = await apiClient.get<Recommendation[]>(`/recommendations/${plantId}`)
  return res.data
}
