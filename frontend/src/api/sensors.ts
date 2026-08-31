import { apiClient } from './client'
import type { SensorReading, SimulationRequest } from './types'

export async function submitSensorReading(data: {
  device_id: string
  crop_id: string
  plant_id: string
  moisture?: number
  ph?: number
  temperature?: number
  humidity?: number
  data_source: 'real' | 'simulated' | 'manual'
}): Promise<SensorReading> {
  const res = await apiClient.post<SensorReading>('/sensors/reading', data)
  return res.data
}

export async function getLatestSensorReading(plantId: string, cropId: string): Promise<SensorReading> {
  const res = await apiClient.get<SensorReading>('/sensors/latest', {
    params: { plant_id: plantId, crop_id: cropId },
  })
  return res.data
}

export async function getSensorHistory(
  plantId: string,
  cropId: string,
  range: '1h' | '6h' | '1d' | '7d' | '30d' = '1d'
): Promise<{ readings: SensorReading[]; range: string; count: number }> {
  const res = await apiClient.get('/sensors/history', {
    params: { plant_id: plantId, crop_id: cropId, range },
  })
  return res.data
}

export async function simulateSensors(req: SimulationRequest): Promise<SensorReading[]> {
  const res = await apiClient.post<SensorReading[]>('/sensors/simulate', req)
  return res.data
}
