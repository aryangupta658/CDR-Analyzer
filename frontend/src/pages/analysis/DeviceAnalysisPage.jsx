import { Cpu, History, Network, Search } from "lucide-react";

import { useState } from "react";
import { toast } from "react-toastify";

import {
  getCommonDevices,
  getDeviceHistory,
  getImeiAnalysis,
  getImsiAnalysis,
} from "../../api/forensicApi";

import EvidenceContextCard from "../../components/analysis/EvidenceContextCard";

import Button from "../../components/common/Button";
import PageHeader from "../../components/common/PageHeader";

import AnalysisResult from "../../components/results/AnalysisResult";

import CommonDeviceGraph from "../../components/visualizations/CommonDeviceGraph";
import DeviceTimeline from "../../components/visualizations/DeviceTimeline";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

export default function DeviceAnalysisPage() {
  const { selectedCase, selectedEvidence } = useCase();

  const [query, setQuery] = useState("");

  const [result, setResult] = useState(null);

  const [resultTitle, setResultTitle] = useState("");

  const [resultType, setResultType] = useState("");

  const [loading, setLoading] = useState(false);

  const [activeAction, setActiveAction] = useState(null);

  async function execute(action) {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence.");

      return;
    }

    if (action !== "common" && !query.trim()) {
      toast.error("Enter an IMEI, IMSI or phone number.");

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

      if (action === "imei") {
        data = await getImeiAnalysis(
          selectedCase.id,
          selectedEvidence.id,
          query.trim(),
        );

        title = `IMEI Analysis — ${query.trim()}`;

        type = "imei";
      }

      if (action === "imsi") {
        data = await getImsiAnalysis(
          selectedCase.id,
          selectedEvidence.id,
          query.trim(),
        );

        title = `IMSI Analysis — ${query.trim()}`;

        type = "imsi";
      }

      if (action === "history") {
        data = await getDeviceHistory(
          selectedCase.id,
          selectedEvidence.id,
          query.trim(),
        );

        title = `Device History — ${query.trim()}`;

        type = "history";
      }

      if (action === "common") {
        data = await getCommonDevices(selectedCase.id, selectedEvidence.id, {
          minimum_numbers: 2,
          limit: 100,
        });

        title = "Common Device Analysis";

        type = "common";
      }

      setResult(data);
      setResultTitle(title);
      setResultType(type);

      toast.success("Device analysis completed.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Device analysis failed."));
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

  return (
    <>
      <PageHeader
        title="Device Analysis"
        description="Analyse IMEI, IMSI, device-change history and common-device associations."
      />

      <EvidenceContextCard />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
            <Cpu size={22} />
          </span>

          <div>
            <h2 className="font-bold text-slate-950">
              Device identifier search
            </h2>

            <p className="mt-1 text-sm leading-6 text-slate-500">
              Enter an IMEI, IMSI or phone number. The currently selected
              evidence file will be analysed.
            </p>
          </div>
        </div>

        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Enter IMEI, IMSI or phone number"
          className="mt-5 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        />

        <p className="mt-2 text-xs leading-5 text-slate-500">
          Enter an IMEI for IMEI analysis, an IMSI for IMSI analysis, or a phone
          number for device-change history. Common Devices does not require
          input.
        </p>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Button
            loading={loading && activeAction === "imei"}
            disabled={loading || !query.trim()}
            onClick={() => execute("imei")}
          >
            <Search size={17} />
            IMEI Analysis
          </Button>

          <Button
            variant="secondary"
            loading={loading && activeAction === "imsi"}
            disabled={loading || !query.trim()}
            onClick={() => execute("imsi")}
          >
            <Network size={17} />
            IMSI Analysis
          </Button>

          <Button
            variant="secondary"
            loading={loading && activeAction === "history"}
            disabled={loading || !query.trim()}
            onClick={() => execute("history")}
          >
            <History size={17} />
            Device History
          </Button>

          <Button
            variant="orange"
            loading={loading && activeAction === "common"}
            disabled={loading}
            onClick={() => execute("common")}
          >
            <Cpu size={17} />
            Common Devices
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
      </section>

      <AnalysisResult data={result} title={resultTitle} />

      {resultType === "history" && result && (
        <div className="mt-6">
          <DeviceTimeline result={result} />
        </div>
      )}

      {resultType === "common" && result && (
        <div className="mt-6">
          <CommonDeviceGraph result={result} />
        </div>
      )}
    </>
  );
}
