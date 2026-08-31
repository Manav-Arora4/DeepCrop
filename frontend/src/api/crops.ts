import { apiClient } from './client'
import type { CropSummary, CropDetail } from './types'

export async function listCrops(): Promise<CropSummary[]> {
  const res = await apiClient.get<CropSummary[]>('/crops')
  return res.data
}

export async function getCropDetail(cropId: string): Promise<CropDetail> {
  const res = await apiClient.get<CropDetail>(`/crops/${cropId}`)
  return res.data
}

export async function installCrop(cropId: string): Promise<{ status: string; message: string }> {
  const res = await apiClient.post(`/crops/${cropId}/install`)
  return res.data
}
