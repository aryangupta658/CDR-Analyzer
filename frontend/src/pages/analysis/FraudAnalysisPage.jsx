import { useState } from "react";

import {
  AlertTriangle,
  CalendarClock,
  MessageSquareWarning,
  PhoneCall,
  RefreshCw,
  SearchCheck,
} from "lucide-react";

import { runPatternAnalysis } from "../../api/fraudApi";
import { useCase } from "../../context/CaseContext";

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }

  const parsedDate = new Date(value);

  if (Number.isNaN(parsedDate.getTime())) {
    return String(value);
  }

  return parsedDate.toLocaleString("en-IN");
}

function getScopeLabel(scope) {
  if (scope === "incident") {
    return "Incident patterns";
  }

  if (scope === "short_window") {
    return "Short-window patterns";
  }

  return "Full-evidence patterns";
}

function getScopeDescription(scope) {
  if (scope === "incident") {
    return "Patterns found by comparing activity around the selected incident date and time with the number's normal behaviour.";
  }

  if (scope === "short_window") {
    return "Rapid bursts and technical changes found inside minutes, one hour or twenty-four hours.";
  }

  return "Patterns calculated across the complete selected evidence period.";
}

function SummaryCard({ title, value, description, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
          <p className="mt-2 text-sm text-slate-500">{description}</p>
        </div>

        <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}

function ValueChips({ values, emptyText = "No values available" }) {
  if (!Array.isArray(values) || values.length === 0) {
    return <p className="mt-2 text-sm text-slate-500">{emptyText}</p>;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {values.map((value) => (
        <span
          key={value}
          className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700"
        >
          {value}
        </span>
      ))}
    </div>
  );
}

function PatternCard({ pattern }) {
  return (
    <article className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <h4 className="font-bold text-slate-900">{pattern.title}</h4>

          <p className="mt-2 text-sm leading-6 text-slate-600">
            {pattern.description}
          </p>
        </div>

        <div className="shrink-0 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 lg:max-w-64">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
            Observed
          </p>
          <p className="mt-1 break-words font-bold text-blue-900">
            {String(pattern.observed_value)}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Category
          </p>
          <p className="mt-1 font-medium capitalize text-slate-800">
            {pattern.category}
          </p>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Compared with
          </p>
          <p className="mt-1 font-medium text-slate-800">
            {pattern.comparison_value || "No fixed comparison required"}
          </p>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Supporting records
          </p>
          <p className="mt-1 font-medium text-slate-800">
            {pattern.source_record_ids.length}
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4">
        <p className="text-sm leading-6 text-slate-700">
          {pattern.explanation}
        </p>

        <p className="mt-2 text-xs text-slate-500">
          Evidence period: {formatDateTime(pattern.window_start)} to{" "}
          {formatDateTime(pattern.window_end)}
        </p>
      </div>

      {pattern.related_numbers?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Related numbers
          </p>
          <ValueChips values={pattern.related_numbers} />
        </div>
      )}

      {pattern.imeis?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            IMEI values
          </p>
          <ValueChips values={pattern.imeis} />
        </div>
      )}

      {pattern.imsis?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            IMSI values
          </p>
          <ValueChips values={pattern.imsis} />
        </div>
      )}

      {pattern.cell_ids?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Cell IDs
          </p>
          <ValueChips values={pattern.cell_ids} />
        </div>
      )}
    </article>
  );
}

function NumberPatternGroup({ summary, patterns }) {
  const scopeOrder = ["short_window", "full_evidence", "incident"];

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-blue-100 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
              Number pattern details
            </p>
            <h3 className="mt-1 text-xl font-bold text-slate-950">
              {summary.phone_number}
            </h3>
          </div>

          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <span className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-blue-700">
              {summary.total_patterns} total patterns
            </span>
            <span className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-blue-700">
              {summary.short_window_patterns} short window
            </span>
            <span className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-blue-700">
              {summary.full_evidence_patterns} full evidence
            </span>
            {summary.incident_patterns > 0 && (
              <span className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-blue-700">
                {summary.incident_patterns} incident
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-6 p-5">
        {scopeOrder.map((scope) => {
          const scopePatterns = patterns.filter(
            (pattern) => pattern.scope === scope,
          );

          if (scopePatterns.length === 0) {
            return null;
          }

          return (
            <section key={scope}>
              <div className="mb-3 rounded-xl border border-blue-100 bg-blue-50/60 p-4">
                <h4 className="font-bold text-blue-900">
                  {getScopeLabel(scope)}
                </h4>
                <p className="mt-1 text-sm leading-6 text-blue-700">
                  {getScopeDescription(scope)}
                </p>
              </div>

              <div className="space-y-4">
                {scopePatterns.map((pattern) => (
                  <PatternCard key={pattern.pattern_id} pattern={pattern} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

export default function FraudAnalysisPage() {
  const caseContext = useCase();

  const selectedCase =
    caseContext.selectedCase || caseContext.currentCase || null;

  const selectedEvidence =
    caseContext.selectedEvidence ||
    caseContext.activeEvidence ||
    caseContext.currentEvidence ||
    null;

  const [phoneNumber, setPhoneNumber] = useState("");
  const [incidentDateTime, setIncidentDateTime] = useState("");
  const [incidentCellIds, setIncidentCellIds] = useState("");

  const [patterns, setPatterns] = useState({
    calls: true,
    sms: true,
    devices: true,
    locations: true,
    roaming: true,
    forwarding: true,
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function togglePattern(patternName) {
    setPatterns((currentPatterns) => ({
      ...currentPatterns,
      [patternName]: !currentPatterns[patternName],
    }));
  }

  async function handleAnalyse() {
    setError("");
    setResult(null);

    if (!selectedCase?.id) {
      setError("Select or open a case first.");
      return;
    }

    if (!selectedEvidence?.id) {
      setError("Select an imported evidence file first.");
      return;
    }

    const evidenceStatus = String(selectedEvidence.status || "")
      .trim()
      .toLowerCase();

    if (evidenceStatus && evidenceStatus !== "imported") {
      setError(
        "The selected evidence must be imported before pattern analysis.",
      );
      return;
    }

    if (!Object.values(patterns).some(Boolean)) {
      setError("Enable at least one pattern category.");
      return;
    }

    setLoading(true);

    try {
      const response = await runPatternAnalysis({
        caseId: selectedCase.id,
        evidenceId: selectedEvidence.id,
        phoneNumber,
        incidentDateTime,
        incidentCellIds,
        includeCallPatterns: patterns.calls,
        includeSmsPatterns: patterns.sms,
        includeDevicePatterns: patterns.devices,
        includeLocationPatterns: patterns.locations,
        includeRoamingPatterns: patterns.roaming,
        includeForwardingPatterns: patterns.forwarding,
      });

      setResult(response);
    } catch (requestError) {
      const backendDetail = requestError?.response?.data?.detail;
      setError(
        typeof backendDetail === "string"
          ? backendDetail
          : requestError?.message || "Pattern analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  const patternsByNumber = result
    ? result.patterns.reduce((groupedPatterns, pattern) => {
        if (!groupedPatterns[pattern.phone_number]) {
          groupedPatterns[pattern.phone_number] = [];
        }

        groupedPatterns[pattern.phone_number].push(pattern);
        return groupedPatterns;
      }, {})
    : {};

  const summariesWithPatterns = result
    ? result.number_summaries.filter((item) => item.total_patterns > 0)
    : [];

  return (
    <main className="space-y-6 p-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">
          Communication Pattern Analysis
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          Detect short-window, full-evidence and optional incident-time
          communication patterns.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
            Current case
          </p>
          <p className="mt-1 font-bold text-slate-900">
            {selectedCase?.title || "No case selected"}
          </p>
          <p className="mt-1 text-sm text-blue-700">
            {selectedCase?.case_number || "Open a case to continue"}
          </p>
        </div>

        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
            Active evidence
          </p>
          <p className="mt-1 font-bold text-slate-900">
            {selectedEvidence?.original_filename ||
              selectedEvidence?.filename ||
              selectedEvidence?.file_name ||
              "No evidence selected"}
          </p>
          <p className="mt-1 text-sm text-emerald-700">
            Evidence ID: {selectedEvidence?.id || "—"}
            {selectedEvidence?.status ? ` · ${selectedEvidence.status}` : ""}
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <label
            htmlFor="pattern-phone-number"
            className="text-sm font-semibold text-slate-700"
          >
            Phone number
          </label>

          <input
            id="pattern-phone-number"
            type="text"
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
            placeholder="Leave empty to analyse every number in the evidence"
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />

          <p className="mt-2 text-xs text-slate-500">
            Enter one number to restrict the analysis, or leave it empty to
            analyse target numbers and every contact number found in the CDR.
          </p>
        </div>

        <div className="mt-5">
          <label
            htmlFor="pattern-incident-datetime"
            className="text-sm font-semibold text-slate-700"
          >
            Incident date and time (optional)
          </label>

          <input
            id="pattern-incident-datetime"
            type="datetime-local"
            value={incidentDateTime}
            onChange={(event) => setIncidentDateTime(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />

          <p className="mt-2 text-xs text-slate-500">
            Leave empty for short-window and full-evidence patterns. Select a
            date and time to also apply incident-day comparison rules.
          </p>
        </div>

        {incidentDateTime && (
          <div className="mt-5">
            <label
              htmlFor="pattern-incident-cell-ids"
              className="text-sm font-semibold text-slate-700"
            >
              Incident cell IDs (optional)
            </label>

            <input
              id="pattern-incident-cell-ids"
              type="text"
              value={incidentCellIds}
              onChange={(event) => setIncidentCellIds(event.target.value)}
              placeholder="CGI00426, CGI00427"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <p className="mt-2 text-xs text-slate-500">
              Enter comma-separated CGI or cell IDs only when you want to check
              whether a number appeared at an incident tower.
            </p>
          </div>
        )}

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["calls", "Call patterns"],
            ["sms", "SMS patterns"],
            ["devices", "Device and SIM patterns"],
            ["locations", "Location patterns"],
            ["roaming", "Roaming patterns"],
            ["forwarding", "Forwarding patterns"],
          ].map(([patternName, label]) => (
            <label
              key={patternName}
              className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 transition hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={patterns[patternName]}
                onChange={() => togglePattern(patternName)}
                className="h-4 w-4 accent-blue-600"
              />

              <span className="text-sm font-medium text-slate-700">
                {label}
              </span>
            </label>
          ))}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="button"
          onClick={handleAnalyse}
          disabled={loading}
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
            <RefreshCw size={18} className="animate-spin" />
          ) : (
            <SearchCheck size={18} />
          )}

          {loading ? "Analysing records..." : "Run Pattern Analysis"}
        </button>
      </section>

      {result && (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard
              title="Detected patterns"
              value={result.total_patterns}
              description={`${result.analysed_numbers} numbers analysed`}
              icon={SearchCheck}
            />

            <SummaryCard
              title="Short-window patterns"
              value={result.short_window_patterns}
              description="Bursts and rapid activity changes"
              icon={PhoneCall}
            />

            <SummaryCard
              title="Full-evidence patterns"
              value={result.full_evidence_patterns}
              description={`${result.evidence_days} evidence day(s)`}
              icon={MessageSquareWarning}
            />

            <SummaryCard
              title="Incident patterns"
              value={result.incident_patterns}
              description={
                result.incident_rules_applied
                  ? "Incident comparison enabled"
                  : "Incident date not selected"
              }
              icon={CalendarClock}
            />
          </section>

          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <div className="flex gap-3">
              <AlertTriangle
                className="mt-0.5 shrink-0 text-amber-700"
                size={20}
              />
              <p className="text-sm text-amber-900">{result.disclaimer}</p>
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-5">
              <h2 className="text-lg font-bold text-slate-900">
                Number pattern overview
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Every phone number found in the selected CDR is analysed. A zero
                means that the current rules did not detect a pattern for that
                number.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Number</th>
                    <th className="px-4 py-3">Patterns</th>
                    <th className="px-4 py-3">Short window</th>
                    <th className="px-4 py-3">Full evidence</th>
                    <th className="px-4 py-3">Incident</th>
                    <th className="px-4 py-3">Devices</th>
                    <th className="px-4 py-3">Contacts</th>
                  </tr>
                </thead>

                <tbody>
                  {result.number_summaries.map((item) => (
                    <tr
                      key={item.phone_number}
                      className="border-t border-slate-100"
                    >
                      <td className="px-4 py-3 font-semibold text-slate-900">
                        {item.phone_number}
                      </td>
                      <td className="px-4 py-3">{item.total_patterns}</td>
                      <td className="px-4 py-3">
                        {item.short_window_patterns}
                      </td>
                      <td className="px-4 py-3">
                        {item.full_evidence_patterns}
                      </td>
                      <td className="px-4 py-3">{item.incident_patterns}</td>
                      <td className="px-4 py-3">{item.device_patterns}</td>
                      <td className="px-4 py-3">{item.contact_patterns}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="space-y-5">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Pattern details by number
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Each number is shown once. Its short-window, full-evidence and
                incident patterns are placed in separate readable sections.
              </p>
            </div>

            {summariesWithPatterns.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
                <SearchCheck size={38} className="mx-auto text-slate-300" />
                <p className="mt-3 font-semibold text-slate-700">
                  No configured pattern was detected
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  This only means that the current pattern conditions were not
                  met in the selected evidence.
                </p>
              </div>
            ) : (
              summariesWithPatterns.map((summary) => (
                <NumberPatternGroup
                  key={summary.phone_number}
                  summary={summary}
                  patterns={patternsByNumber[summary.phone_number] || []}
                />
              ))
            )}
          </section>
        </>
      )}
    </main>
  );
}
