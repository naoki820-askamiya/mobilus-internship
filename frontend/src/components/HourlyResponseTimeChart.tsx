import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { HourlySummaryResponse } from '../types';
import { formatDuration } from '../utils/formatDuration';
import styles from './SummaryChart.module.css';

const CHART_TICKS = [0, 6, 12, 18, 23];

interface HourlyResponseTimeChartProps {
  data: HourlySummaryResponse[];
}

interface ResponseTimeTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload?: HourlySummaryResponse;
  }>;
}

function formatHour(hour: number): string {
  return `${hour}:00`;
}

function ResponseTimeTooltip({ active, payload }: ResponseTimeTooltipProps) {
  const item = payload?.[0]?.payload;
  if (
    !active ||
    !item ||
    item.average_first_response_seconds === null
  ) {
    return null;
  }

  return (
    <div className={styles.tooltip}>
      <p>{formatHour(item.hour)}</p>
      <p className={styles.tooltipValue}>
        平均初回応答時間:{' '}
        {formatDuration(item.average_first_response_seconds)}
      </p>
    </div>
  );
}

/**
 * 応答済みセッションの平均初回応答時間を時間帯別に表示する
 */
export function HourlyResponseTimeChart({
  data,
}: HourlyResponseTimeChartProps) {
  return (
    <div
      className={styles.chart}
      role="img"
      aria-label="選択日の1時間ごとの平均初回応答時間を示す折れ線グラフ"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 16, right: 20, bottom: 8, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="hour"
            ticks={CHART_TICKS}
            tickFormatter={formatHour}
            tick={{ fill: '#666', fontSize: 12 }}
          />
          <YAxis
            domain={[0, 'auto']}
            allowDecimals={false}
            tickFormatter={formatDuration}
            tick={{ fill: '#666', fontSize: 12 }}
            width={68}
          />
          <Tooltip content={<ResponseTimeTooltip />} />
          <Line
            type="monotone"
            dataKey="average_first_response_seconds"
            stroke="#1976d2"
            strokeWidth={3}
            dot={{ r: 4, fill: '#1976d2' }}
            activeDot={{ r: 6 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
