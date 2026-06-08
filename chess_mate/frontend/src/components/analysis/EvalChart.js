import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { useTheme } from '../../context/ThemeContext';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

const EvalChart = ({ points = [], selectedIndex = 0, onSelectIndex, height = 180 }) => {
  const { isDarkMode } = useTheme();

  const chartData = useMemo(() => {
    const labels = points.map((point, index) => `Move ${point.label ?? index + 1}`);
    const values = points.map((point) => point.value);

    return {
      labels,
      datasets: [
        {
          label: 'Eval',
          data: values,
          borderColor: isDarkMode ? 'rgb(96, 165, 250)' : 'rgb(59, 130, 246)',
          backgroundColor: isDarkMode ? 'rgba(96, 165, 250, 0.15)' : 'rgba(59, 130, 246, 0.12)',
          pointRadius: points.map((_, index) => (index === selectedIndex ? 5 : 2)),
          pointBackgroundColor: points.map((_, index) =>
            (index === selectedIndex
              ? (isDarkMode ? 'rgb(250, 204, 21)' : 'rgb(234, 179, 8)')
              : (isDarkMode ? 'rgb(96, 165, 250)' : 'rgb(59, 130, 246)'))
          ),
          tension: 0.35,
          fill: true,
        },
      ],
    };
  }, [points, selectedIndex, isDarkMode]);

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `Eval: ${Number(context.parsed.y).toFixed(2)}`,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          maxTicksLimit: 12,
          color: isDarkMode ? '#9ca3af' : '#6b7280',
        },
        grid: { color: isDarkMode ? 'rgba(55,65,81,0.5)' : 'rgba(229,231,235,0.8)' },
      },
      y: {
        ticks: { color: isDarkMode ? '#9ca3af' : '#6b7280' },
        grid: { color: isDarkMode ? 'rgba(55,65,81,0.5)' : 'rgba(229,231,235,0.8)' },
      },
    },
    onClick: (_, elements) => {
      if (!onSelectIndex || !elements?.length) {
        return;
      }
      onSelectIndex(elements[0].index);
    },
  }), [isDarkMode, onSelectIndex]);

  if (!points.length) {
    return null;
  }

  return (
    <div style={{ height }} aria-label="Evaluation chart">
      <Line data={chartData} options={options} />
    </div>
  );
};

export default EvalChart;
