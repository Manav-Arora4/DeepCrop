export interface ThresholdValue {
  value: number | null
  status: 'LOW' | 'OPTIMAL' | 'HIGH' | 'UNKNOWN'
  unit: string
}

export interface ThresholdStatus {
  moisture?: ThresholdValue
  ph?: ThresholdValue
  temperature?: ThresholdValue
  humidity?: ThresholdValue
  [key: string]: ThresholdValue | undefined
}

export interface SensorReading {
  id: number
  device_id: string
  crop_id: string
  plant_id: string
  moisture: number | null
  ph: number | null
  temperature: number | null
  humidity: number | null
  data_source: 'real' | 'simulated' | 'manual'
  threshold_status: ThresholdStatus
  timestamp: string
}

export interface CVPrediction {
  id: number
  crop: string
  disease: string
  disease_id: string
  confidence: number
  severity: string | null
  model_version: string
  model_status: 'ready' | 'demo' | 'unavailable' | 'error'
  low_confidence_warning: boolean
  plant_id: string
  timestamp: string
}

export interface DiseaseRiskPrediction {
  id: number
  crop_id: string
  plant_id: string
  risk_score: number
  risk_level: 'low' | 'moderate' | 'high' | 'critical' | 'unknown'
  contributing_factors: string[]
  model_version: string
  model_status: 'ready' | 'demo'
  timestamp: string
}

export interface Recommendation {
  id: number
  crop_id: string
  plant_id: string
  summary: string
  contributing_factors: string[]
  recommended_actions: string[]
  prevention_steps: string[]
  monitoring_advice: string | null
  urgency: string
  sources: Array<{ title: string; topic: string; relevance: number }>
  llm_provider: string
  llm_model: string
  timestamp: string
}

export interface CropSummary {
  id: string
  name: string
  installed: boolean
  version: string
  description: string
  growth_stages: string[]
}

export interface CropDetail extends CropSummary {
  thresholds: Record<string, {
    low_max: number
    optimal_min: number
    optimal_max: number
    high_min: number
    unit: string
    notes?: string
  }> | null
  disease_classes: Array<{
    id: string
    index: number
    display: string
    is_healthy: boolean
    treatment_urgency: string
    pathogen_type?: string
    causative_agent?: string
  }> | null
  cv_model_status: string
  risk_model_status: string
}

export interface SimulationRequest {
  crop_id: string
  plant_id: string
  scenario: 'optimal' | 'drought' | 'overwatered' | 'disease_risk' | 'random'
  count: number
}
