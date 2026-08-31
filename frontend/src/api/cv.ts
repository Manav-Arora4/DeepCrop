import { apiClient } from './client'
import type { CVPrediction } from './types'

export async function predictDisease(
  file: File,
  cropId: string,
  plantId: string,
  sensorReadingId?: number
): Promise<CVPrediction> {
  const form = new FormData()
  form.append('file', file)
  form.append('crop_id', cropId)
  form.append('plant_id', plantId)
  if (sensorReadingId) {
    form.append('sensor_reading_id', sensorReadingId.toString())
  }

  const res = await apiClient.post<CVPrediction>('/cv/predict', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getPlantCVHistory(plantId: string): Promise<CVPrediction[]> {
  const res = await apiClient.get<CVPrediction[]>(`/cv/predictions/${plantId}`)
  return res.data
}
