import { ArrowRight } from "lucide-react";
import { Link } from "react-router";

export default function AnalysisCard({
  title,
  description,
  icon: Icon,
  to,
  iconClass,
}) {
  return (
    <Link
      to={to}
      className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-md"
    >
      <span
        className={`
          flex h-12 w-12 items-center
          justify-center rounded-xl
          ${iconClass}
        `}
      >
        <Icon size={23} />
      </span>

      <h3 className="mt-5 font-bold text-slate-950">{title}</h3>

      <p className="mt-2 min-h-12 text-sm leading-6 text-slate-500">
        {description}
      </p>

      <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-blue-600">
        Open module
        <ArrowRight
          size={16}
          className="transition group-hover:translate-x-1"
        />
      </span>
    </Link>
  );
}
