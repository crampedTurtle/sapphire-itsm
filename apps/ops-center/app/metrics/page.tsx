'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { opsApi } from "@/lib/api"
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMetrics()
  }, [])

  async function loadMetrics() {
    setLoading(true)
    try {
      const intakeMetrics = await opsApi.getIntakeMetrics()
      setMetrics(intakeMetrics)
    } catch (error) {
      console.error('Error loading metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading...</div>
  }

  // Mock data for charts
  const intakeOverTime = [
    { date: 'Mon', intake: 45 },
    { date: 'Tue', intake: 52 },
    { date: 'Wed', intake: 38 },
    { date: 'Thu', intake: 61 },
    { date: 'Fri', intake: 55 },
    { date: 'Sat', intake: 28 },
    { date: 'Sun', intake: 22 },
  ]

  const intentDistribution = metrics ? Object.entries(metrics.by_intent).map(([name, value]) => ({
    name,
    value
  })) : []

  const topTenants = [
    { tenant: 'Acme Corp', cases: 23 },
    { tenant: 'TechCo', cases: 18 },
    { tenant: 'StartupXYZ', cases: 15 },
    { tenant: 'BigCorp', cases: 12 },
    { tenant: 'SmallBiz', cases: 8 },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Metrics & Trends</h1>
        <p className="mt-1 text-sm text-gray-500">Weekly / monthly control</p>
      </div>

      {/* Intake Volume Over Time */}
      <Card>
        <CardHeader>
          <CardTitle>Intake Volume Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={intakeOverTime}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="intake" stroke="#0088FE" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Intent Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Intent Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={intentDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {intentDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top 10 Noisiest Tenants */}
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Noisiest Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topTenants}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="tenant" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="cases" fill="#0088FE" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Tier 0 Deflection Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">65%</div>
            <p className="text-sm text-gray-500 mt-1">Last 7 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Intent Misclassification Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">8.2%</div>
            <p className="text-sm text-gray-500 mt-1">Last 30 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Reopen Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">12.5%</div>
            <p className="text-sm text-gray-500 mt-1">Last 30 days</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

