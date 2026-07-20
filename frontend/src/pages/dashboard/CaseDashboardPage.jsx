import {
  Clock3,
  FileSpreadsheet,
  MapPinned,
  PhoneCall,
  Smartphone,
} from "lucide-react";

import { useEffect, useMemo, useState } from "react";

import { toast } from "react-toastify";

import { Link, Navigate, useParams } from "react-router";

import { getCaseSummary } from "../../api/analysisApi";

import { getEvidence } from "../../api/evidenceApi";

import LoadingSpinner from "../../components/common/LoadingSpinner";
import PageHeader from "../../components/common/PageHeader";
import AnalysisCard from "../../components/dashboard/AnalysisCard";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

function normalizeStatus(status) {
  return String(status || "")
    .trim()
    .toLowerCase();
}

function formatDuration(seconds) {
  const totalSeconds = Number(seconds) || 0;

  const hours = Math.floor(totalSeconds / 3600);

  const minutes = Math.floor((totalSeconds % 3600) / 60);

  const remainingSeconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${remainingSeconds}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-IN").format(Number(value) || 0);
}

export default function CaseDashboardPage() {
  const { caseId } = useParams();

  const { selectedCase, selectedEvidence, selectEvidence } = useCase();

  const [summary, setSummary] = useState(null);

  const [evidenceFiles, setEvidenceFiles] = useState([]);

  const [loading, setLoading] = useState(true);

  const [summaryLoading, setSummaryLoading] = useState(false);

  const importedEvidenceFiles = useMemo(
    () =>
      evidenceFiles.filter(
        (item) => normalizeStatus(item.status) === "imported",
      ),
    [evidenceFiles],
  );

  useEffect(() => {
    if (!caseId) {
      return;
    }

    loadEvidenceFiles();
  }, [caseId]);

  useEffect(() => {
    if (!caseId || !selectedEvidence?.id) {
      setSummary(null);
      return;
    }

    loadEvidenceSummary(selectedEvidence.id);
  }, [caseId, selectedEvidence?.id]);

  async function loadEvidenceFiles() {
    setLoading(true);

    try {
      const evidenceResult = await getEvidence(caseId);

      const files = Array.isArray(evidenceResult)
        ? evidenceResult
        : evidenceResult.items || evidenceResult.evidence || [];

      setEvidenceFiles(files);

      const imported = files.filter(
        (item) => normalizeStatus(item.status) === "imported",
      );

      const selectedStillExists =
        selectedEvidence &&
        imported.some(
          (item) => String(item.id) === String(selectedEvidence.id),
        );

      if (!selectedStillExists) {
        if (imported.length > 0) {
          selectEvidence(imported[0]);
        }
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load evidence files."));
    } finally {
      setLoading(false);
    }
  }

  async function loadEvidenceSummary(evidenceId) {
    setSummaryLoading(true);

    try {
      const result = await getCaseSummary(caseId, evidenceId);

      setSummary(result);
    } catch (error) {
      setSummary(null);

      toast.error(
        getErrorMessage(error, "Could not load the selected evidence summary."),
      );
    } finally {
      setSummaryLoading(false);
    }
  }

  function handleEvidenceChange(event) {
    const evidenceId = event.target.value;

    const evidence = importedEvidenceFiles.find(
      (item) => String(item.id) === evidenceId,
    );

    if (!evidence) {
      return;
    }

    selectEvidence(evidence);

    toast.success(`Evidence ${evidence.id} selected.`);
  }

  if (!caseId) {
    return <Navigate to="/app/cases" replace />;
  }

  if (!selectedCase) {
    return <Navigate to="/app/cases" replace />;
  }

  if (loading) {
    return <LoadingSpinner text="Loading case dashboard..." />;
  }

  const selectedCaseTitle = selectedCase.title || `Case ${caseId}`;

  const analysisModules = [
    {
      title: "Number Analysis",
      description:
        "Number profiles, common contacts, top contacts and communication activity.",
      icon: PhoneCall,
      iconClass: "bg-blue-50 text-blue-600",
      to: "/app/analysis/numbers",
    },
    {
      title: "Device Analysis",
      description:
        "IMEI, IMSI, device-change history and common-device detection.",
      icon: Smartphone,
      iconClass: "bg-violet-50 text-violet-600",
      to: "/app/analysis/devices",
    },
    {
      title: "Location Analysis",
      description:
        "Tower summaries, location history, co-location and movement.",
      icon: MapPinned,
      iconClass: "bg-emerald-50 text-emerald-600",
      to: "/app/analysis/locations",
    },
    {
      title: "Incident Analysis",
      description:
        "Communication and tower activity around selected incident times.",
      icon: Clock3,
      iconClass: "bg-orange-50 text-orange-600",
      to: "/app/analysis/incidents",
    },
  ];

  const summaryCards = [
    {
      label: "Evidence Records",
      value: formatNumber(summary?.total_records),
    },
    {
      label: "Unique Numbers",
      value: formatNumber(summary?.unique_numbers),
    },
    {
      label: "Total Duration",
      value: formatDuration(summary?.total_duration_seconds),
    },
    {
      label: "Cell Towers",
      value: formatNumber(summary?.unique_cell_ids),
    },
  ];

  return (
    <>
      <PageHeader
        title={selectedCaseTitle}
        description="Overview of the selected case and its imported evidence."
        action={
          <Link
            to={`/app/cases/${caseId}/evidence`}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
          >
            <FileSpreadsheet size={17} />
            Upload / View Evidence
          </Link>
        }
      />

      <section className="mb-7 rounded-2xl border border-blue-100 bg-blue-50/60 p-5">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <h2 className="font-semibold text-slate-900">Active evidence</h2>

            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              Only successfully imported evidence files are displayed. Dashboard
              totals and forensic analysis use the selected evidence.
            </p>
          </div>

          <label className="block w-full lg:max-w-lg">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Imported evidence
            </span>

            <select
              value={selectedEvidence?.id || ""}
              onChange={handleEvidenceChange}
              disabled={importedEvidenceFiles.length === 0}
              className="min-h-12 w-full rounded-xl border border-blue-200 bg-white px-4 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
            >
              {importedEvidenceFiles.length === 0 ? (
                <option value="">No imported evidence</option>
              ) : (
                <>
                  <option value="">Select imported evidence</option>

                  {importedEvidenceFiles.map((item) => (
                    <option key={item.id} value={item.id}>
                      Evidence {item.id} —{" "}
                      {item.original_filename || item.filename || "CDR file"}
                    </option>
                  ))}
                </>
              )}
            </select>
          </label>
        </div>

        {selectedEvidence && (
          <div className="mt-5 flex flex-wrap gap-3 text-xs">
            <span className="rounded-full bg-white px-3 py-1.5 font-semibold text-blue-700">
              Evidence ID: {selectedEvidence.id}
            </span>

            <span className="max-w-full truncate rounded-full bg-white px-3 py-1.5 font-semibold text-slate-600">
              {selectedEvidence.original_filename ||
                selectedEvidence.filename ||
                "Imported evidence"}
            </span>

            <span className="rounded-full bg-emerald-100 px-3 py-1.5 font-semibold text-emerald-700">
              Imported
            </span>
          </div>
        )}
      </section>

      {importedEvidenceFiles.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-orange-300 bg-orange-50 p-8 text-center">
          <h2 className="font-bold text-orange-900">No imported evidence</h2>

          <p className="mt-2 text-sm text-orange-700">
            Upload and import a CDR file before opening the analysis modules.
          </p>

          <Link
            to={`/app/cases/${caseId}/evidence`}
            className="mt-5 inline-flex rounded-xl bg-orange-500 px-5 py-3 text-sm font-semibold text-white hover:bg-orange-600"
          >
            Upload Evidence
          </Link>
        </section>
      ) : (
        <>
          {summaryLoading ? (
            <LoadingSpinner text="Calculating selected evidence totals..." />
          ) : (
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {summaryCards.map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <p className="text-sm font-medium text-slate-500">
                    {item.label}
                  </p>

                  <p className="mt-2 break-words text-2xl font-bold text-slate-950">
                    {item.value}
                  </p>
                </div>
              ))}
            </section>
          )}

          {summary && (
            <section className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  label: "Outgoing records",
                  value: summary.outgoing_records,
                },
                {
                  label: "Incoming records",
                  value: summary.incoming_records,
                },
                {
                  label: "Unique IMEIs",
                  value: summary.unique_imeis,
                },
                {
                  label: "Unique IMSIs",
                  value: summary.unique_imsis,
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    {item.label}
                  </p>

                  <p className="mt-2 text-xl font-bold text-slate-900">
                    {formatNumber(item.value)}
                  </p>
                </div>
              ))}
            </section>
          )}

          <section className="mt-8">
            <div>
              <h2 className="text-xl font-bold text-slate-950">
                Analysis modules
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                These modules use evidence{" "}
                {selectedEvidence?.id || "not selected"}.
              </p>
            </div>

            {!selectedEvidence && (
              <div className="mt-4 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
                <p className="text-sm font-medium text-orange-700">
                  Select an imported evidence file before running analysis.
                </p>
              </div>
            )}

            <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              {analysisModules.map((module) => (
                <AnalysisCard key={module.title} {...module} />
              ))}
            </div>
          </section>
        </>
      )}

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold text-slate-950">Case information</h2>

        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Case number
            </p>

            <p className="mt-1 font-medium text-slate-800">
              {selectedCase.case_number || `Case ${caseId}`}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Case title
            </p>

            <p className="mt-1 font-medium text-slate-800">
              {selectedCaseTitle}
            </p>
          </div>

          <div className="sm:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Description
            </p>

            <p className="mt-1 text-sm leading-6 text-slate-600">
              {selectedCase.description || "No case description was provided."}
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
