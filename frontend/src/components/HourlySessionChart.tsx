import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { HourlySummaryResponse } from '../types';
import styles from './SummaryChart.module.css';

const CHART_TICKS = [0, 6, 12, 18, 23];

interface HourlySessionChartProps {
  data: HourlySummaryResponse[];
}

interface SessionTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload?: HourlySummaryResponse;
  }>;
}

function formatHour(hour: number): string {
  return `${hour}:00`;
}

function SessionTooltip({ active, payload }: SessionTooltipProps) {
  const item = payload?.[0]?.payload;
  if (!active || !item) return null;

  return (
    <div className={styles.tooltip}>
      <p>{formatHour(item.hour)}</p>
      <p className={styles.tooltipValue}>
        セッション数: {item.session_count}件
      </p>
    </div>
  );
}

/**
 * 選択日に開始したセッション数を時間帯別に表示する
 */
export function HourlySessionChart({ data }: HourlySessionChartProps) {
  return (
    <div
      className={styles.chart}
      role="img"
      aria-label="選択日の1時間ごとのセッション数を示す棒グラフ"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 16, right: 20, bottom: 8, left: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="hour"
            ticks={CHART_TICKS}
            tickFormatter={formatHour}
            tick={{ fill: '#666', fontSize: 12 }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: '#666', fontSize: 12 }}
            width={40}
            label={{
              value: '件',
              angle: -90,
              position: 'insideLeft',
              fill: '#666',
            }}
          />
          <Tooltip content={<SessionTooltip />} />
          <Bar
            dataKey="session_count"
            fill="#1976d2"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
