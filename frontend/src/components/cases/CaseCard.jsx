import { ArrowRight } from "lucide-react";

export default function CaseCard({ caseData, onOpen }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            {caseData.case_number || `Case ${caseData.id}`}
          </p>

          <h3 className="mt-1 font-bold text-slate-950">
            {caseData.title || `Case ${caseData.id}`}
          </h3>

          <p className="mt-2 line-clamp-2 text-sm text-slate-500">
            {caseData.description || "No description provided."}
          </p>
        </div>

        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
          {caseData.status || "Active"}
        </span>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
        <span className="text-xs text-slate-400">Case ID: {caseData.id}</span>

        <button
          type="button"
          onClick={() => onOpen(caseData)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700"
        >
          Open
          <ArrowRight size={16} />
        </button>
      </div>
    </article>
  );
}
