import {
  BarChart,
  Bar,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function ChartCard({ title, description, children }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="font-bold text-slate-950">{title}</h3>

      {description && (
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      )}

      <div className="mt-5 h-72">{children}</div>
    </article>
  );
}

function activityDescription(phoneNumber, grouping) {
  if (!phoneNumber) {
    return `CDR records grouped by ${grouping}.`;
  }

  return `Only records involving ${phoneNumber}, grouped by ${grouping}.`;
}

export function HourlyActivityChart({ activity, phoneNumber = "" }) {
  const chartData = (activity || []).map((item) => ({
    hour: `${String(item.hour).padStart(2, "0")}:00`,
    records: item.record_count,
    duration: item.total_duration_seconds,
  }));

  return (
    <ChartCard
      title="Activity by hour"
      description={activityDescription(phoneNumber, "hour of the day")}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="hour" interval={2} fontSize={11} />
          <YAxis allowDecimals={false} fontSize={11} />
          <Tooltip />
          <Bar
            dataKey="records"
            name="Records"
            fill="#2563eb"
            radius={[6, 6, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function DailyActivityChart({ activity, phoneNumber = "" }) {
  const chartData = (activity || []).map((item) => ({
    date: item.activity_date,
    records: item.record_count,
    duration: item.total_duration_seconds,
  }));

  return (
    <ChartCard
      title="Activity by date"
      description={activityDescription(phoneNumber, "calendar date")}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" fontSize={11} />
          <YAxis allowDecimals={false} fontSize={11} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="records"
            name="Records"
            stroke="#2563eb"
            strokeWidth={3}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
