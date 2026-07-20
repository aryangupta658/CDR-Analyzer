import { MapPin, MapPinned, RadioTower, Route } from "lucide-react";

import { useState } from "react";
import { toast } from "react-toastify";

import {
  getCoLocation,
  getNumberLocationHistory,
  getTowerDetail,
  getTowerSummary,
} from "../../api/locationApi";

import EvidenceContextCard from "../../components/analysis/EvidenceContextCard";

import Button from "../../components/common/Button";
import PageHeader from "../../components/common/PageHeader";

import AnalysisResult from "../../components/results/AnalysisResult";

import TowerMap from "../../components/visualizations/TowerMap";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN");
}

function formatDuration(seconds) {
  const totalSeconds = Math.max(0, Number(seconds) || 0);
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

function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  return String(value);
}

function formatCoordinate(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return String(value);
  }

  return numericValue.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
}

function NumberChips({ numbers }) {
  if (!Array.isArray(numbers) || numbers.length === 0) {
    return <p className="mt-3 text-sm text-slate-500">No numbers found.</p>;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {numbers.map((number) => (
        <span
          key={number}
          className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700"
        >
          {number}
        </span>
      ))}
    </div>
  );
}

function TowerSummaryView({ result }) {
  const towers = Array.isArray(result?.towers) ? result.towers : [];

  return (
    <section className="mt-6 space-y-5">
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <h2 className="text-lg font-bold text-slate-950">Tower Summary</h2>
            <p className="mt-1 text-sm text-slate-500">
              First and last coordinates are read directly from the imported CDR
              fields. Legacy LAC and tower-address columns are not shown.
            </p>
          </div>

          <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            {result?.tower_count ?? towers.length} cell IDs
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3">Cell ID</th>
                <th className="px-4 py-3">First Latitude</th>
                <th className="px-4 py-3">First Longitude</th>
                <th className="px-4 py-3">Last Latitude</th>
                <th className="px-4 py-3">Last Longitude</th>
                <th className="px-4 py-3">Total Records</th>
                <th className="px-4 py-3">Unique Numbers</th>
                <th className="px-4 py-3">First Seen</th>
                <th className="px-4 py-3">Last Seen</th>
              </tr>
            </thead>

            <tbody>
              {towers.map((tower) => (
                <tr key={tower.cell_id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-semibold text-blue-700">
                    {tower.cell_id}
                  </td>
                  <td className="px-4 py-3">
                    {formatCoordinate(tower.first_latitude)}
                  </td>
                  <td className="px-4 py-3">
                    {formatCoordinate(tower.first_longitude)}
                  </td>
                  <td className="px-4 py-3">
                    {formatCoordinate(tower.last_latitude)}
                  </td>
                  <td className="px-4 py-3">
                    {formatCoordinate(tower.last_longitude)}
                  </td>
                  <td className="px-4 py-3">{tower.total_records}</td>
                  <td className="px-4 py-3">{tower.unique_number_count}</td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {formatDateTime(tower.first_seen)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {formatDateTime(tower.last_seen)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {towers.length === 0 && (
          <div className="p-8 text-center text-sm text-slate-500">
            No tower records were found in the selected evidence.
          </div>
        )}
      </div>

      {towers.length > 0 && (
        <section>
          <div>
            <h2 className="text-lg font-bold text-slate-950">
              Unique numbers by cell ID
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Each section is labelled with its actual cell ID instead of
              generic names such as Result 1 or Result 2.
            </p>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {towers.map((tower) => (
              <article
                key={`numbers-${tower.cell_id}`}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
                      Cell ID
                    </p>
                    <h3 className="mt-1 text-lg font-bold text-slate-950">
                      {tower.cell_id}
                    </h3>
                  </div>

                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                    {tower.unique_number_count} unique numbers
                  </span>
                </div>

                <NumberChips numbers={tower.unique_numbers} />
              </article>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

function LocationHistoryView({ result, title }) {
  const history = Array.isArray(result?.history) ? result.history : [];

  return (
    <section className="mt-6 space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <h2 className="text-lg font-bold text-slate-950">
              {title || "Location History"}
            </h2>

            <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">
              The table follows the 23-field operator CDR format. FIRST_CGI,
              LAST_CGI, coordinates, IMEI and IMSI are associated with
              TARGET_NO—not with B_PARTY.
            </p>
          </div>

          <span className="w-fit shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            {result?.total_location_records ?? history.length} location records
          </span>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Unique CGI values
            </p>
            <p className="mt-2 text-xl font-bold text-slate-950">
              {result?.unique_tower_count ?? 0}
            </p>
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Unique first CGI
            </p>
            <p className="mt-2 text-xl font-bold text-slate-950">
              {result?.unique_first_cell_count ?? 0}
            </p>
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              First activity
            </p>
            <p className="mt-2 text-sm font-bold text-slate-950">
              {formatDateTime(result?.first_seen)}
            </p>
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Last activity
            </p>
            <p className="mt-2 text-sm font-bold text-slate-950">
              {formatDateTime(result?.last_seen)}
            </p>
          </div>
        </div>

        <div className="mt-5 rounded-xl border border-amber-100 bg-amber-50 p-4">
          <p className="text-sm leading-6 text-amber-800">
            {result?.association_basis ||
              "The displayed cells represent approximate network locations of the target subscriber."}
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <h3 className="font-bold text-slate-950">History</h3>
            <p className="mt-1 text-sm text-slate-500">
              Records are ordered by CALL_TIME from earliest to latest.
            </p>
          </div>

          <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            {history.length} shown
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[2200px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="whitespace-nowrap px-4 py-3">PAN No</th>
                <th className="whitespace-nowrap px-4 py-3">Source Row</th>
                <th className="whitespace-nowrap px-4 py-3">Call Time</th>
                <th className="whitespace-nowrap px-4 py-3">Target No</th>
                <th className="whitespace-nowrap px-4 py-3">Call Type</th>
                <th className="whitespace-nowrap px-4 py-3">TOC</th>
                <th className="whitespace-nowrap px-4 py-3">B Party</th>
                <th className="whitespace-nowrap px-4 py-3">Duration</th>
                <th className="whitespace-nowrap px-4 py-3">First CGI</th>
                <th className="whitespace-nowrap px-4 py-3">First Latitude</th>
                <th className="whitespace-nowrap px-4 py-3">First Longitude</th>
                <th className="whitespace-nowrap px-4 py-3">Last CGI</th>
                <th className="whitespace-nowrap px-4 py-3">Last Latitude</th>
                <th className="whitespace-nowrap px-4 py-3">Last Longitude</th>
                <th className="whitespace-nowrap px-4 py-3">IMEI</th>
                <th className="whitespace-nowrap px-4 py-3">IMSI</th>
                <th className="whitespace-nowrap px-4 py-3">Location Change</th>
              </tr>
            </thead>

            <tbody>
              {history.map((item) => (
                <tr
                  key={item.record_id}
                  className="border-t border-slate-100 text-slate-700"
                >
                  <td className="whitespace-nowrap px-4 py-3">
                    {displayValue(item.pan_no)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {displayValue(item.source_row)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    <p className="font-medium text-slate-900">
                      {formatDateTime(item.start_datetime)}
                    </p>

                    {item.call_time_raw && (
                      <p className="mt-1 text-xs text-slate-400">
                        Raw: {item.call_time_raw}
                      </p>
                    )}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 font-semibold text-blue-700">
                    {displayValue(item.target_number)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold uppercase text-blue-700">
                      {displayValue(item.call_type)}
                    </span>
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {displayValue(item.connection_type)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {displayValue(item.b_party_number)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {formatDuration(item.duration_seconds)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 font-semibold text-emerald-700">
                    {displayValue(item.first_cell_global_id)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {formatCoordinate(item.first_latitude)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {formatCoordinate(item.first_longitude)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 font-semibold text-violet-700">
                    {displayValue(item.last_cell_global_id)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {formatCoordinate(item.last_latitude)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {formatCoordinate(item.last_longitude)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {displayValue(item.imei)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    {displayValue(item.imsi)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        item.location_changed
                          ? "bg-orange-50 text-orange-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {item.location_changed ? "Changed" : "No change"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {history.length === 0 && (
          <div className="p-8 text-center text-sm text-slate-500">
            No location history was found for this TARGET_NO.
          </div>
        )}
      </div>
    </section>
  );
}

export default function LocationAnalysisPage() {
  const { selectedCase, selectedEvidence } = useCase();

  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [resultTitle, setResultTitle] = useState("");
  const [resultType, setResultType] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState(null);

  async function execute(action) {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence file.");
      return;
    }

    if (action !== "towers" && !query.trim()) {
      toast.error("Enter a cell ID, phone number or comma-separated numbers.");
      return;
    }

    setLoading(true);
    setActiveAction(action);
    setResult(null);
    setResultTitle("");
    setResultType("");

    try {
      let data = null;
      let title = "";
      let type = "";

      if (action === "towers") {
        data = await getTowerSummary(selectedCase.id, selectedEvidence.id, {
          limit: 1000,
        });
        title = "Tower Summary";
        type = "towers";
      }

      if (action === "tower-detail") {
        data = await getTowerDetail(
          selectedCase.id,
          selectedEvidence.id,
          query.trim(),
        );
        title = `Tower Detail — ${query.trim()}`;
        type = "tower-detail";
      }

      if (action === "history") {
        data = await getNumberLocationHistory(
          selectedCase.id,
          selectedEvidence.id,
          query.trim(),
        );
        title = `Location History — ${query.trim()}`;
        type = "history";
      }

      if (action === "co-location") {
        const numbers = query
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

        if (numbers.length < 2) {
          toast.error("Enter at least two comma-separated phone numbers.");
          return;
        }

        data = await getCoLocation(selectedCase.id, selectedEvidence.id, {
          target_numbers: numbers,
          tolerance_minutes: 15,
          limit: 100,
        });
        title = "Tower-Level Co-location Analysis";
        type = "co-location";
      }

      setResult(data);
      setResultTitle(title);
      setResultType(type);
      toast.success("Location analysis completed.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Location analysis failed."));
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  }

  function clearResult() {
    setQuery("");
    setResult(null);
    setResultTitle("");
    setResultType("");
  }

  const resultSupportsMap = [
    "towers",
    "tower-detail",
    "history",
    "co-location",
  ].includes(resultType);

  return (
    <>
      <PageHeader
        title="Location Analysis"
        description="Analyse tower usage, location history and possible tower-level co-location."
      />

      <EvidenceContextCard />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
            <MapPinned size={22} />
          </span>

          <div>
            <h2 className="font-bold text-slate-950">
              Location and tower search
            </h2>

            <p className="mt-1 text-sm leading-6 text-slate-500">
              Use a cell ID for tower detail, a phone number for location
              history, or multiple phone numbers for co-location analysis.
            </p>
          </div>
        </div>

        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="CGI01892, phone number or comma-separated numbers"
          className="mt-5 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        />

        <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
          <p>
            Tower detail:{" "}
            <span className="font-semibold text-slate-700">CGI01892</span>
          </p>

          <p>
            Location history:{" "}
            <span className="font-semibold text-slate-700">9876500001</span>
          </p>

          <p>
            Co-location:{" "}
            <span className="font-semibold text-slate-700">
              9876500001, 9876500002
            </span>
          </p>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Button
            loading={loading && activeAction === "towers"}
            disabled={loading}
            onClick={() => execute("towers")}
          >
            <RadioTower size={17} />
            Tower Summary
          </Button>

          <Button
            variant="secondary"
            loading={loading && activeAction === "tower-detail"}
            disabled={loading || !query.trim()}
            onClick={() => execute("tower-detail")}
          >
            <MapPin size={17} />
            Tower Detail
          </Button>

          <Button
            variant="secondary"
            loading={loading && activeAction === "history"}
            disabled={loading || !query.trim()}
            onClick={() => execute("history")}
          >
            <Route size={17} />
            Location History
          </Button>

          <Button
            variant="orange"
            loading={loading && activeAction === "co-location"}
            disabled={loading || !query.trim()}
            onClick={() => execute("co-location")}
          >
            <MapPinned size={17} />
            Co-location
          </Button>
        </div>

        {(query || result) && (
          <div className="mt-5 flex justify-end">
            <button
              type="button"
              onClick={clearResult}
              disabled={loading}
              className="text-sm font-semibold text-slate-500 transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear search and result
            </button>
          </div>
        )}

        <div className="mt-5 rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
          <p className="text-sm font-medium text-emerald-800">
            Interpretation note
          </p>

          <p className="mt-1 text-sm leading-6 text-emerald-700">
            A matching cell ID means that records were associated with the same
            mobile tower. It does not prove that two people were standing at the
            exact same physical point.
          </p>
        </div>
      </section>

      {result && resultType === "towers" ? (
        <TowerSummaryView result={result} />
      ) : result && resultType === "history" ? (
        <LocationHistoryView result={result} title={resultTitle} />
      ) : (
        <AnalysisResult data={result} title={resultTitle} />
      )}

      {result && resultSupportsMap && (
        <div className="mt-6">
          <TowerMap
            result={result}
            showMovementPath={resultType === "history"}
          />
        </div>
      )}
    </>
  );
}
