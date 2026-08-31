import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import SensorsPage from './pages/SensorsPage'
import CVPage from './pages/CVPage'
import RecommendationsPage from './pages/RecommendationsPage'
import CropsPage from './pages/CropsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="sensors" element={<SensorsPage />} />
        <Route path="cv" element={<CVPage />} />
        <Route path="recommendations" element={<RecommendationsPage />} />
        <Route path="crops" element={<CropsPage />} />
      </Route>
    </Routes>
  )
}
