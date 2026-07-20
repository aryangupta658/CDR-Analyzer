import { CheckCircle2, FileSpreadsheet, UploadCloud } from "lucide-react";

import { useEffect, useState } from "react";

import { toast } from "react-toastify";

import { useNavigate, useParams } from "react-router";

import {
  getEvidence,
  importEvidence,
  uploadEvidence,
} from "../../api/evidenceApi";

import Button from "../../components/common/Button";
import EmptyState from "../../components/common/EmptyState";
import LoadingSpinner from "../../components/common/LoadingSpinner";
import PageHeader from "../../components/common/PageHeader";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

const defaultMapping = {
  caller_number: "Calling Number",
  receiver_number: "Called Number",

  start_datetime: null,

  event_date: "Date",
  event_time: "Time",

  end_datetime: null,

  duration_seconds: "Duration",
  event_type: "Call Type",
  direction: "Direction",

  imei: "IMEI",
  imsi: "IMSI",

  cell_id: "Cell ID",
  lac: "LAC",

  latitude: "Latitude",
  longitude: "Longitude",

  tower_address: "Tower Address",
  service_provider: "Provider",
  roaming: "Roaming",
};

export default function UploadEvidencePage() {
  const { caseId } = useParams();

  const navigate = useNavigate();

  const { selectedCase, selectEvidence } = useCase();

  const [file, setFile] = useState(null);

  const [evidenceFiles, setEvidenceFiles] = useState([]);

  const [loading, setLoading] = useState(true);

  const [uploading, setUploading] = useState(false);

  const [importingId, setImportingId] = useState(null);

  useEffect(() => {
    loadEvidence();
  }, [caseId]);

  async function loadEvidence() {
    setLoading(true);

    try {
      const result = await getEvidence(caseId);

      const files = Array.isArray(result)
        ? result
        : result.items || result.evidence || [];

      setEvidenceFiles(files);
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load evidence."));
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!file) {
      toast.error("Select a CDR file first.");

      return;
    }

    setUploading(true);

    try {
      const result = await uploadEvidence(caseId, file);

      toast.success("Evidence uploaded successfully.");

      setFile(null);

      const evidence = result.evidence || result;

      await loadEvidence();

      /*
       * After uploading, automatically start the import
       * when the backend returns the evidence ID.
       */
      if (evidence?.id) {
        await handleImport(evidence);
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Evidence upload was unsuccessful."));
    } finally {
      setUploading(false);
    }
  }

  async function handleImport(evidence) {
    if (!evidence?.id) {
      toast.error("Evidence ID was not found.");

      return;
    }

    setImportingId(evidence.id);

    try {
      const result = await importEvidence(evidence.id, {
        mapping: defaultMapping,
        day_first: true,
        replace_existing: false,
      });

      toast.success(
        `Evidence imported successfully. ${
          result.imported_records ?? 0
        } records added.`,
      );

      selectEvidence({
        ...evidence,
        status: "imported",
      });

      await loadEvidence();
    } catch (error) {
      toast.error(
        getErrorMessage(
          error,
          "Evidence import was unsuccessful. Check the column mapping.",
        ),
      );
    } finally {
      setImportingId(null);
    }
  }

  function continueToDashboard(evidence) {
    selectEvidence(evidence);

    navigate(`/app/cases/${caseId}/dashboard`);
  }

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0] || null;

    setFile(selectedFile);
  }

  const selectedCaseTitle = selectedCase?.title || `Case ${caseId}`;

  return (
    <>
      <PageHeader
        title="Upload evidence files"
        description={`Upload CDR evidence for ${selectedCaseTitle}.`}
      />

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <label className="flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-blue-200 bg-blue-50/40 p-6 text-center transition hover:border-blue-400 hover:bg-blue-50/70">
          <UploadCloud size={45} className="text-blue-600" />

          <p className="mt-4 font-semibold text-slate-900">
            Drag a file here or click to browse
          </p>

          <p className="mt-2 text-sm text-slate-500">
            CSV and XLSX files are supported.
          </p>

          {file && (
            <div className="mt-4 rounded-xl border border-blue-100 bg-white px-4 py-3">
              <p className="text-sm font-semibold text-blue-700">{file.name}</p>

              <p className="mt-1 text-xs text-slate-500">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          )}

          <input
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={handleFileChange}
          />
        </label>

        <div className="mt-5 flex flex-col justify-end gap-3 sm:flex-row">
          {file && (
            <Button variant="secondary" onClick={() => setFile(null)}>
              Clear File
            </Button>
          )}

          <Button loading={uploading} disabled={!file} onClick={handleUpload}>
            Upload File
          </Button>
        </div>
      </div>

      <section className="mt-8">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-950">Evidence files</h2>

          <p className="mt-1 text-sm text-slate-500">
            Uploaded and imported evidence belonging to this case.
          </p>
        </div>

        {loading ? (
          <LoadingSpinner text="Loading evidence files..." />
        ) : evidenceFiles.length === 0 ? (
          <EmptyState
            title="No evidence uploaded"
            description="Upload a CSV or XLSX CDR file to continue."
          />
        ) : (
          <div className="space-y-3">
            {evidenceFiles.map((evidence) => {
              const isImported = evidence.status === "imported";

              const isImporting = importingId === evidence.id;

              return (
                <article
                  key={evidence.id}
                  className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 sm:flex-row sm:items-center"
                >
                  <div className="flex min-w-0 items-center gap-4">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                      <FileSpreadsheet />
                    </span>

                    <div className="min-w-0">
                      <h3 className="truncate font-semibold text-slate-900">
                        {evidence.original_filename ||
                          evidence.filename ||
                          `Evidence ${evidence.id}`}
                      </h3>

                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span>Evidence ID: {evidence.id}</span>

                        <span>•</span>

                        <span
                          className={`
                              rounded-full px-2.5 py-1
                              font-semibold
                              ${
                                isImported
                                  ? "bg-emerald-50 text-emerald-700"
                                  : evidence.status === "failed"
                                    ? "bg-red-50 text-red-700"
                                    : "bg-orange-50 text-orange-700"
                              }
                            `}
                        >
                          {evidence.status || "uploaded"}
                        </span>

                        {evidence.record_count !== undefined && (
                          <>
                            <span>•</span>

                            <span>Records: {evidence.record_count}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {!isImported && (
                      <Button
                        variant="secondary"
                        loading={isImporting}
                        onClick={() => handleImport(evidence)}
                      >
                        Import Evidence
                      </Button>
                    )}

                    {isImported && (
                      <Button onClick={() => continueToDashboard(evidence)}>
                        <CheckCircle2 size={17} />
                        Continue to Dashboard
                      </Button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
