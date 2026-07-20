import { BriefcaseBusiness, FileCheck2 } from "lucide-react";

import { Link } from "react-router";

import { useCase } from "../../context/CaseContext";

export default function EvidenceContextCard() {
  const { selectedCase, selectedEvidence } = useCase();

  if (!selectedCase || !selectedEvidence) {
    return null;
  }

  const filename =
    selectedEvidence.original_filename ||
    selectedEvidence.filename ||
    `Evidence ${selectedEvidence.id}`;

  return (
    <section className="mb-6 rounded-2xl border border-blue-100 bg-blue-50/60 p-4 sm:p-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-blue-600 shadow-sm">
              <BriefcaseBusiness size={19} />
            </span>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
                Current case
              </p>

              <p className="mt-1 font-bold text-slate-900">
                {selectedCase.title}
              </p>

              <p className="mt-1 text-xs text-blue-700">
                {selectedCase.case_number}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-600 shadow-sm">
              <FileCheck2 size={19} />
            </span>

            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
                Active evidence
              </p>

              <p className="mt-1 font-bold text-slate-900">
                Evidence {selectedEvidence.id}
              </p>

              <p className="mt-1 max-w-xs truncate text-xs text-slate-500">
                {filename}
              </p>
            </div>
          </div>
        </div>

        <Link
          to={`/app/cases/${selectedCase.id}/dashboard`}
          className="inline-flex min-h-10 items-center justify-center rounded-xl border border-blue-200 bg-white px-4 text-sm font-semibold text-blue-700 transition hover:bg-blue-50"
        >
          Change Evidence
        </Link>
      </div>
    </section>
  );
}
