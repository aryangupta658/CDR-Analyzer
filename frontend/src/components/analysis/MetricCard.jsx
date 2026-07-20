export default function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  iconClass = "bg-blue-50 text-blue-600",
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>

          <p className="mt-2 break-words text-2xl font-bold text-slate-950">
            {value}
          </p>

          {description && (
            <p className="mt-2 text-xs leading-5 text-slate-400">
              {description}
            </p>
          )}
        </div>

        {Icon && (
          <span
            className={`
              flex h-11 w-11 shrink-0
              items-center justify-center
              rounded-xl
              ${iconClass}
            `}
          >
            <Icon size={20} />
          </span>
        )}
      </div>
    </article>
  );
}
