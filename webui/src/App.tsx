import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function App() {
  const [gcPruneRuns, setGcPruneRuns] = useState<number | null>(null)
  const [rebalanceSuccess, setRebalanceSuccess] = useState<number | null>(null)

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const response = await axios.get('http://192.168.69.119:6060/metrics')
        const data = response.data as string

        const gcRunsMatch = data.match(/gc_prune_runs_total (\d+)/)
        const rebalanceSuccessMatch = data.match(/rebalance_success_total (\d+)/)

        if (gcRunsMatch) setGcPruneRuns(parseInt(gcRunsMatch[1], 10))
        if (rebalanceSuccessMatch) setRebalanceSuccess(parseInt(rebalanceSuccessMatch[1], 10))
      } catch (error) {
        console.error('Failed to fetch metrics:', error)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col p-6">
      {/* Hero Header */}
      <header className="text-center mb-8">
        <h1 className="text-5xl font-extrabold text-gray-800 dark:text-gray-200">Swarm-Orch Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-2 text-lg">Live Metrics and Health Monitoring</p>
      </header>

      {/* Button Row */}
      <div className="flex justify-end mb-6">
        <Button variant="outline" onClick={() => window.location.reload()}>
          🔄 Refresh
        </Button>
      </div>

      {/* Metric Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mx-auto w-full max-w-6xl">
        {/* GC Prune Runs */}
        <Card>
          <CardHeader>
            <CardTitle>GC Prune Runs</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">{gcPruneRuns !== null ? gcPruneRuns : 'Loading...'}</p>
            <Badge variant="outline" className="mt-2">Updated Live</Badge>
          </CardContent>
        </Card>

        {/* Rebalance Success */}
        <Card>
          <CardHeader>
            <CardTitle>Rebalance Success</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-4xl font-bold text-green-600 dark:text-green-400">{rebalanceSuccess !== null ? rebalanceSuccess : 'Loading...'}</p>
            <Badge variant="outline" className="mt-2">Updated Live</Badge>
          </CardContent>
        </Card>

        {/* Placeholder Metric */}
        <Card>
          <CardHeader>
            <CardTitle>Anchor Updates</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">Soon</p>
            <Badge variant="secondary" className="mt-2">Coming Soon</Badge>
          </CardContent>
        </Card>

        {/* Placeholder Metric */}
        <Card>
          <CardHeader>
            <CardTitle>Autoheal Events</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-4xl font-bold text-yellow-500 dark:text-yellow-300">Soon</p>
            <Badge variant="secondary" className="mt-2">Coming Soon</Badge>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default App
