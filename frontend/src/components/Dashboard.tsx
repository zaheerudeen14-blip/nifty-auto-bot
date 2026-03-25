import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ArrowUp, ArrowDown, Minus, Bell } from "lucide-react";

// NOTE: Replace API URLs with your backend (Angel One integration)

interface HeatmapRow {
  strike: number;
  ce: number;
  ceChange: number;
  pe: number;
  peChange: number;
}

interface SupportResistance {
  strike: number;
  change: number;
  strength: number;
}

interface Summary {
  spot: number;
  pcr: number;
  signal: "Bullish" | "Bearish" | "Neutral";
  resistance: SupportResistance;
  support: SupportResistance;
}

export default function Dashboard() {
  const [heatmap, setHeatmap] = useState<HeatmapRow[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [alerts, setAlerts] = useState<string[]>([]);

  // 🔄 Fetch Heatmap every 3 mins
  useEffect(() => {
    const fetchHeatmap = async () => {
      try {
        const res = await fetch("/api/heatmap");
        const data = await res.json();
        setHeatmap(data);
      } catch {}
    };
    fetchHeatmap();
    const interval = setInterval(fetchHeatmap, 180000);
    return () => clearInterval(interval);
  }, []);

  // 📊 Fetch Market Bias (15 min logic)
  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const res = await fetch("/api/summary");
        const data = await res.json();
        setSummary(data);
      } catch {}
    };
    fetchSummary();
    const interval = setInterval(fetchSummary, 900000);
    return () => clearInterval(interval);
  }, []);

  // 🚨 Fetch Alerts (Support/Resistance weakening)
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await fetch("/api/alerts");
        const data = await res.json();
        setAlerts(data);
      } catch {}
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 900000);
    return () => clearInterval(interval);
  }, []);

  if (!summary) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <p className="text-gray-400 text-sm">Connecting to market data…</p>
        </div>
      </div>
    );
  }

  const signalColor =
    summary.signal === "Bullish"
      ? "bg-green-500"
      : summary.signal === "Bearish"
      ? "bg-red-500"
      : "bg-yellow-500";

  const SignalIcon =
    summary.signal === "Bullish"
      ? ArrowUp
      : summary.signal === "Bearish"
      ? ArrowDown
      : Minus;

  return (
    <div className="p-4 grid gap-4 bg-black text-white min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <h1 className="text-lg font-bold tracking-wide text-white">
          🤖 Nifty Auto Bot
        </h1>
        <span className="text-xs text-zinc-500">
          {new Date().toLocaleDateString("en-IN", {
            weekday: "short",
            day: "numeric",
            month: "short",
          })}
        </span>
      </div>

      {/* TradingView Style Header Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900">
          <CardContent className="p-4">
            <p className="text-gray-400 text-sm">NIFTY Spot</p>
            <h2 className="text-2xl font-bold">{summary.spot}</h2>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900">
          <CardContent className="p-4">
            <p className="text-gray-400 text-sm">PCR (15m)</p>
            <h2 className="text-2xl font-bold">{summary.pcr}</h2>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900">
          <CardContent className="p-4 flex justify-between items-center">
            <div>
              <p className="text-gray-400 text-sm">Market Bias</p>
              <Badge className={`${signalColor} text-white`}>
                {summary.signal}
              </Badge>
            </div>
            <SignalIcon className="text-gray-300" />
          </CardContent>
        </Card>

        <Card className="bg-zinc-900">
          <CardContent className="p-4">
            <p className="text-gray-400 text-sm">Updated</p>
            <h2 className="text-lg font-semibold">
              {new Date().toLocaleTimeString("en-IN")}
            </h2>
          </CardContent>
        </Card>
      </div>

      {/* TradingView Chart Embed */}
      <Card className="bg-zinc-900">
        <CardContent className="p-2">
          <iframe
            title="TradingView Chart"
            src="https://www.tradingview.com/widgetembed/?symbol=NSE:NIFTY&interval=5&theme=dark&style=1&locale=en"
            className="w-full h-[400px] rounded-lg"
          />
        </CardContent>
      </Card>

      {/* Support & Resistance */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="bg-zinc-900">
          <CardContent className="p-4">
            <h3 className="text-red-400 font-semibold mb-2">🔴 Resistance</h3>
            <p className="text-sm text-gray-300">
              Strike: <span className="font-bold">{summary.resistance.strike}</span>
            </p>
            <p className="text-sm text-gray-300 mb-2">
              OI Change: <span className="font-bold">{summary.resistance.change}</span>
            </p>
            <Progress value={summary.resistance.strength} />
          </CardContent>
        </Card>

        <Card className="bg-zinc-900">
          <CardContent className="p-4">
            <h3 className="text-green-400 font-semibold mb-2">🟢 Support</h3>
            <p className="text-sm text-gray-300">
              Strike: <span className="font-bold">{summary.support.strike}</span>
            </p>
            <p className="text-sm text-gray-300 mb-2">
              OI Change: <span className="font-bold">{summary.support.change}</span>
            </p>
            <Progress value={summary.support.strength} />
          </CardContent>
        </Card>
      </div>

      {/* OI Heatmap */}
      <Card className="bg-zinc-900">
        <CardContent className="p-4">
          <h3 className="mb-3 font-semibold">📊 OI Heatmap (3m refresh)</h3>
          <div className="grid grid-cols-5 text-xs text-gray-400 font-semibold pb-1 border-b border-zinc-700">
            <div>Strike</div>
            <div>CE OI</div>
            <div>CE Δ</div>
            <div>PE OI</div>
            <div>PE Δ</div>
          </div>
          {heatmap.length === 0 ? (
            <p className="text-xs text-zinc-600 pt-3">No heatmap data yet.</p>
          ) : (
            heatmap.map((row) => (
              <div
                key={row.strike}
                className="grid grid-cols-5 py-1 text-sm border-b border-zinc-800 hover:bg-zinc-800 transition-colors"
              >
                <div className="font-medium">{row.strike}</div>
                <div className="text-red-400">{row.ce}</div>
                <div
                  className={
                    row.ceChange > 0 ? "text-green-400" : "text-red-400"
                  }
                >
                  {row.ceChange}
                </div>
                <div className="text-green-400">{row.pe}</div>
                <div
                  className={
                    row.peChange > 0 ? "text-green-400" : "text-red-400"
                  }
                >
                  {row.peChange}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Alerts */}
      <Card className="bg-zinc-900">
        <CardContent className="p-4">
          <h3 className="flex items-center gap-2 font-semibold mb-2">
            <Bell size={16} className="text-yellow-400" /> Alerts (15m logic)
          </h3>
          {alerts.length === 0 ? (
            <p className="text-xs text-zinc-600">No alerts at this time.</p>
          ) : (
            alerts.map((a, i) => (
              <div
                key={i}
                className="py-1 text-sm text-yellow-300 border-b border-zinc-800"
              >
                ⚠ {a}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
