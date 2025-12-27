import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface GottmanRadarProps {
  criticism: number;
  contempt: number;
  defensiveness: number;
  stonewalling: number;
  delay?: number;
}

export const GottmanRadar: React.FC<GottmanRadarProps> = ({
  criticism,
  contempt,
  defensiveness,
  stonewalling,
  delay = 0,
}) => {
  const [isAnimated, setIsAnimated] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsAnimated(true), delay * 1000);
    return () => clearTimeout(timer);
  }, [delay]);

  // Normalize scores to 0-1 range for radar
  const normalize = (value: number) => Math.min(value / 10, 1);

  const data = [
    { label: 'Criticism', value: normalize(criticism), color: '#F59E0B' },
    { label: 'Contempt', value: normalize(contempt), color: '#EF4444' },
    { label: 'Defensiveness', value: normalize(defensiveness), color: '#8B5CF6' },
    { label: 'Stonewalling', value: normalize(stonewalling), color: '#3B82F6' },
  ];

  // SVG dimensions
  const size = 280;
  const center = size / 2;
  const maxRadius = 100;
  const levels = 5;

  // Calculate polygon points
  const getPolygonPoints = (values: number[]) => {
    const angleStep = (2 * Math.PI) / values.length;
    return values.map((value, index) => {
      const angle = index * angleStep - Math.PI / 2; // Start from top
      const radius = value * maxRadius;
      const x = center + radius * Math.cos(angle);
      const y = center + radius * Math.sin(angle);
      return `${x},${y}`;
    }).join(' ');
  };

  const dataPoints = isAnimated ? data.map(d => d.value) : [0, 0, 0, 0];

  // Get label positions
  const getLabelPosition = (index: number) => {
    const angleStep = (2 * Math.PI) / 4;
    const angle = index * angleStep - Math.PI / 2;
    const radius = maxRadius + 35;
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  };

  // Calculate total score
  const totalScore = criticism + contempt + defensiveness + stonewalling;
  const maxTotal = 40;
  const healthLevel = totalScore <= 10 ? 'healthy' : totalScore <= 20 ? 'moderate' : totalScore <= 30 ? 'concerning' : 'critical';

  const healthColors = {
    healthy: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'Healthy' },
    moderate: { bg: 'bg-amber-50', text: 'text-amber-600', label: 'Moderate' },
    concerning: { bg: 'bg-orange-50', text: 'text-orange-600', label: 'Concerning' },
    critical: { bg: 'bg-red-50', text: 'text-red-600', label: 'Critical' },
  };

  const status = healthColors[healthLevel];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-6 shadow-glass"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-warmGray-800">Four Horsemen</h3>
          <p className="text-xs text-warmGray-500">Relationship risk indicators</p>
        </div>
        <div className={`px-3 py-1.5 rounded-full ${status.bg}`}>
          <span className={`text-sm font-medium ${status.text}`}>{status.label}</span>
        </div>
      </div>

      {/* Radar Chart */}
      <div className="flex justify-center">
        <svg width={size} height={size} className="overflow-visible">
          {/* Background circles */}
          {Array.from({ length: levels }).map((_, i) => {
            const radius = ((i + 1) / levels) * maxRadius;
            return (
              <circle
                key={i}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="#E7E5E4"
                strokeWidth={1}
                strokeDasharray={i === levels - 1 ? "none" : "4 4"}
              />
            );
          })}

          {/* Axis lines */}
          {data.map((_, i) => {
            const angle = (i * 2 * Math.PI) / 4 - Math.PI / 2;
            const x2 = center + maxRadius * Math.cos(angle);
            const y2 = center + maxRadius * Math.sin(angle);
            return (
              <line
                key={i}
                x1={center}
                y1={center}
                x2={x2}
                y2={y2}
                stroke="#D6D3D1"
                strokeWidth={1}
              />
            );
          })}

          {/* Data polygon */}
          <motion.polygon
            points={getPolygonPoints(dataPoints)}
            fill="rgba(244, 63, 94, 0.2)"
            stroke="#F43F5E"
            strokeWidth={2}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: delay + 0.3 }}
          />

          {/* Data points */}
          {dataPoints.map((value, i) => {
            const angle = (i * 2 * Math.PI) / 4 - Math.PI / 2;
            const radius = value * maxRadius;
            const x = center + radius * Math.cos(angle);
            const y = center + radius * Math.sin(angle);
            return (
              <motion.circle
                key={i}
                cx={x}
                cy={y}
                r={5}
                fill={data[i].color}
                stroke="white"
                strokeWidth={2}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.3, delay: delay + 0.5 + i * 0.1 }}
              />
            );
          })}

          {/* Labels */}
          {data.map((d, i) => {
            const pos = getLabelPosition(i);
            return (
              <g key={i}>
                <text
                  x={pos.x}
                  y={pos.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="text-xs font-medium fill-warmGray-600"
                >
                  {d.label}
                </text>
                <text
                  x={pos.x}
                  y={pos.y + 14}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="text-xs font-semibold"
                  fill={d.color}
                >
                  {Math.round(d.value * 10)}/10
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Score bar */}
      <div className="mt-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-warmGray-500">Total Score</span>
          <span className="text-sm font-semibold text-warmGray-800">{totalScore}/{maxTotal}</span>
        </div>
        <div className="h-2 bg-warmGray-100 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${
              healthLevel === 'healthy' ? 'bg-emerald-500' :
              healthLevel === 'moderate' ? 'bg-amber-500' :
              healthLevel === 'concerning' ? 'bg-orange-500' : 'bg-red-500'
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${(totalScore / maxTotal) * 100}%` }}
            transition={{ duration: 1, delay: delay + 0.3, ease: "easeOut" }}
          />
        </div>
        <p className="text-xs text-warmGray-400 mt-2 text-center">
          Lower is better. Contempt is the strongest predictor of relationship failure.
        </p>
      </div>
    </motion.div>
  );
};

export default GottmanRadar;
