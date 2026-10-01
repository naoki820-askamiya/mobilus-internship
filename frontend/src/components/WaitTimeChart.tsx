import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { WaitTimeHistoryResponse } from '../types';
import styles from './WaitTimeChart.module.css';

const HOURS_PER_DAY = 24;
const MINUTES_PER_HOUR = 60;
const SECONDS_PER_MINUTE = 60;
const MINUTES_PER_DAY = HOURS_PER_DAY * MINUTES_PER_HOUR;
const CHART_TICK_INTERVAL_HOURS = 6;
const CHART_TICK_INTERVAL_MINUTES =
  CHART_TICK_INTERVAL_HOURS * MINUTES_PER_HOUR;
const JST_DATE_TIME_PATTERN =
  /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/;

interface WaitTimeChartProps {
  data: WaitTimeHistoryResponse;
}

interface ChartPoint {
  timeOfDayInMinutes: number;
  estimatedWaitMinutes: number;
}

interface WaitTimeTooltipProps {
  active?: boolean;
  payload?: Array<{
    value?: number;
    payload?: ChartPoint;
  }>;
}

function parseTimeOfDayInMinutes(value: string): number | null {
  const match = JST_DATE_TIME_PATTERN.exec(value);
  if (!match) return null;

  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const isInvalidTime =
    hour >= HOURS_PER_DAY ||
    minute >= MINUTES_PER_HOUR ||
    second >= SECONDS_PER_MINUTE;
  if (isInvalidTime) return null;

  return hour * MINUTES_PER_HOUR + minute + second / SECONDS_PER_MINUTE;
}

function formatTimeOfDay(timeOfDayInMinutes: number): string {
  const totalMinutes = Math.floor(timeOfDayInMinutes);
  const hour = Math.floor(totalMinutes / MINUTES_PER_HOUR);
  const minute = totalMinutes % MINUTES_PER_HOUR;
  return `${hour}:${minute.toString().padStart(2, '0')}`;
}

function WaitTimeTooltip({ active, payload }: WaitTimeTooltipProps) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;

  return (
    <div className={styles.tooltip}>
      <p>{formatTimeOfDay(point.timeOfDayInMinutes)}</p>
      <p className={styles.tooltipValue}>
        待ち時間: 約{point.estimatedWaitMinutes}分
      </p>
    </div>
  );
}

/**
 * 集計期間にかかわらず、待ち時間の傾向を0:00から24:00までの時刻軸で表示する
 */
export function WaitTimeChart({ data }: WaitTimeChartProps) {
  const points = data.items.flatMap<ChartPoint>((item) => {
    const timeOfDayInMinutes = parseTimeOfDayInMinutes(item.time);
    return timeOfDayInMinutes === null
      ? []
      : [{
          timeOfDayInMinutes,
          estimatedWaitMinutes: item.estimated_wait_minutes,
        }];
  }).sort(
    (firstPoint, secondPoint) =>
      firstPoint.timeOfDayInMinutes - secondPoint.timeOfDayInMinutes
  );
  const ticks = Array.from(
    { length: MINUTES_PER_DAY / CHART_TICK_INTERVAL_MINUTES + 1 },
    (_, index) => index * CHART_TICK_INTERVAL_MINUTES
  );

  return (
    <div
      className={styles.chart}
      role="img"
      aria-label="過去の利用状況に基づく時間帯ごとの推定待ち時間を示す折れ線グラフ"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={points}
          margin={{ top: 16, right: 20, bottom: 8, left: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="timeOfDayInMinutes"
            type="number"
            domain={[0, MINUTES_PER_DAY]}
            ticks={ticks}
            tickFormatter={formatTimeOfDay}
            tick={{ fill: '#666', fontSize: 12 }}
          />
          <YAxis
            domain={[0, 'auto']}
            allowDecimals={false}
            tick={{ fill: '#666', fontSize: 12 }}
            width={40}
            label={{
              value: '分',
              angle: -90,
              position: 'insideLeft',
              fill: '#666',
            }}
          />
          <Tooltip content={<WaitTimeTooltip />} />
          <Line
            type="monotone"
            dataKey="estimatedWaitMinutes"
            stroke="#1976d2"
            strokeWidth={3}
            dot={{ r: 4, fill: '#1976d2' }}
            activeDot={{ r: 6 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
