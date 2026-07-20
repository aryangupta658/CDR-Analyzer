import { AlarmClock, Clock3, RadioTower } from "lucide-react";

import { useState } from "react";
import { toast } from "react-toastify";

import { getIncidentWindow } from "../../api/forensicApi";

import { getIncidentTower } from "../../api/locationApi";

import EvidenceContextCard from "../../components/analysis/EvidenceContextCard";

import Button from "../../components/common/Button";
import PageHeader from "../../components/common/PageHeader";

import AnalysisResult from "../../components/results/AnalysisResult";

import IncidentTimeline from "../../components/visualizations/IncidentTimeline";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

export default function IncidentAnalysisPage() {
  const { selectedCase, selectedEvidence } = useCase();

  const [incidentDateTime, setIncidentDateTime] = useState("");

  const [cellIds, setCellIds] = useState("");

  const [phoneNumbers, setPhoneNumbers] = useState("");

  const [minutesBefore, setMinutesBefore] = useState(30);

  const [minutesAfter, setMinutesAfter] = useState(30);

  const [result, setResult] = useState(null);

  const [resultTitle, setResultTitle] = useState("");

  const [resultType, setResultType] = useState("");

  const [loading, setLoading] = useState(false);

  const [activeAction, setActiveAction] = useState(null);

  function parsePhoneNumbers() {
    const numbers = phoneNumbers
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    return numbers.length > 0 ? numbers : null;
  }

  function parseCellIds() {
    return cellIds
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function validateCommonInputs() {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence.");

      return false;
    }

    if (!incidentDateTime) {
      toast.error("Select the incident date and time.");

      return false;
    }

    const before = Number(minutesBefore);

    const after = Number(minutesAfter);

    if (Number.isNaN(before) || Number.isNaN(after)) {
      toast.error("Minutes before and after must be valid numbers.");

      return false;
    }

    if (before < 0 || after < 0) {
      toast.error("Minutes before and after cannot be negative.");

      return false;
    }

    if (before > 10080 || after > 10080) {
      toast.error("The maximum supported time window is 10080 minutes.");

      return false;
    }

    return true;
  }

  async function runIncidentWindow() {
    if (!validateCommonInputs()) {
      return;
    }

    setLoading(true);
    setActiveAction("window");
    setResult(null);
    setResultTitle("");
    setResultType("");

    try {
      const data = await getIncidentWindow(selectedCase.id, {
        evidence_id: selectedEvidence.id,

        incident_datetime: incidentDateTime,

        minutes_before: Number(minutesBefore),

        minutes_after: Number(minutesAfter),

        phone_numbers: parsePhoneNumbers(),

        limit: 1000,
      });

      setResult(data);

      setResultTitle("Incident Time-Window Analysis");

      setResultType("window");

      toast.success("Incident-window analysis completed.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Incident-window analysis failed."));
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  }

  async function runIncidentTower() {
    if (!validateCommonInputs()) {
      return;
    }

    const parsedCellIds = parseCellIds();

    if (parsedCellIds.length === 0) {
      toast.error("Enter at least one cell ID.");

      return;
    }

    setLoading(true);
    setActiveAction("tower");
    setResult(null);
    setResultTitle("");
    setResultType("");

    try {
      const data = await getIncidentTower(
        selectedCase.id,
        selectedEvidence.id,
        {
          incident_datetime: incidentDateTime,

          cell_ids: parsedCellIds,

          minutes_before: Number(minutesBefore),

          minutes_after: Number(minutesAfter),

          phone_numbers: parsePhoneNumbers(),

          limit: 1000,
        },
      );

      setResult(data);

      setResultTitle("Incident Tower Analysis");

      setResultType("tower");

      toast.success("Incident-tower analysis completed.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Incident-tower analysis failed."));
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  }

  function clearForm() {
    setIncidentDateTime("");
    setCellIds("");
    setPhoneNumbers("");
    setMinutesBefore(30);
    setMinutesAfter(30);
    setResult(null);
    setResultTitle("");
    setResultType("");
  }

  return (
    <>
      <PageHeader
        title="Incident Analysis"
        description="Examine communication and tower activity before and after a selected incident time."
      />

      <EvidenceContextCard />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-600">
            <AlarmClock size={22} />
          </span>

          <div>
            <h2 className="font-bold text-slate-950">Incident details</h2>

            <p className="mt-1 text-sm leading-6 text-slate-500">
              Select the incident time and define how many minutes before and
              after should be examined.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Incident date and time
            </span>

            <input
              type="datetime-local"
              value={incidentDateTime}
              onChange={(event) => setIncidentDateTime(event.target.value)}
              className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />

            <p className="mt-1 text-xs text-slate-500">
              Make sure the selected AM/PM time matches the imported CDR
              records.
            </p>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Cell IDs</span>

            <input
              type="text"
              value={cellIds}
              onChange={(event) => setCellIds(event.target.value)}
              placeholder="CELL-109, CELL-110"
              className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />

            <p className="mt-1 text-xs text-slate-500">
              Required only for incident tower analysis. Separate multiple cell
              IDs with commas.
            </p>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Minutes before
            </span>

            <input
              type="number"
              min="0"
              max="10080"
              value={minutesBefore}
              onChange={(event) => setMinutesBefore(event.target.value)}
              className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Minutes after
            </span>

            <input
              type="number"
              min="0"
              max="10080"
              value={minutesAfter}
              onChange={(event) => setMinutesAfter(event.target.value)}
              className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </label>

          <label className="block md:col-span-2">
            <span className="text-sm font-medium text-slate-700">
              Phone numbers
            </span>

            <input
              type="text"
              value={phoneNumbers}
              onChange={(event) => setPhoneNumbers(event.target.value)}
              placeholder="Optional: 9876500001, 9876500002"
              className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />

            <p className="mt-1 text-xs text-slate-500">
              Leave empty to include every number found inside the selected
              incident window.
            </p>
          </label>
        </div>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <Button
            loading={loading && activeAction === "window"}
            disabled={loading || !incidentDateTime}
            onClick={runIncidentWindow}
          >
            <Clock3 size={17} />
            Incident Time Window
          </Button>

          <Button
            variant="orange"
            loading={loading && activeAction === "tower"}
            disabled={loading || !incidentDateTime || !cellIds.trim()}
            onClick={runIncidentTower}
          >
            <RadioTower size={17} />
            Incident Tower Analysis
          </Button>

          <Button variant="secondary" disabled={loading} onClick={clearForm}>
            Clear
          </Button>
        </div>

        <div className="mt-5 rounded-xl border border-orange-100 bg-orange-50/60 p-4">
          <p className="text-sm font-medium text-orange-800">
            Interpretation note
          </p>

          <p className="mt-1 text-sm leading-6 text-orange-700">
            Incident analysis displays CDR activity around a selected date and
            time. It does not automatically prove that a person was physically
            present at the exact incident location.
          </p>
        </div>
      </section>

      <AnalysisResult data={result} title={resultTitle} />

      {result && resultType && (
        <div className="mt-6">
          <IncidentTimeline result={result} />
        </div>
      )}
    </>
  );
}
