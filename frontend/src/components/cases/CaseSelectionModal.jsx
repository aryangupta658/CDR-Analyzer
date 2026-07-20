import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import { createCase, getCases } from "../../api/caseApi";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

import Button from "../common/Button";
import EmptyState from "../common/EmptyState";
import LoadingSpinner from "../common/LoadingSpinner";
import Modal from "../common/Modal";
import CaseCard from "./CaseCard";

export default function CaseSelectionModal({ open, onClose, onCaseSelected }) {
  const [tab, setTab] = useState("create");

  const [cases, setCases] = useState([]);

  const [loadingCases, setLoadingCases] = useState(false);

  const [creating, setCreating] = useState(false);

  const [form, setForm] = useState({
    case_number: "",
    title: "",
    description: "",
  });

  const { selectCase } = useCase();

  useEffect(() => {
    if (open && tab === "existing") {
      loadCases();
    }
  }, [open, tab]);

  async function loadCases() {
    setLoadingCases(true);

    try {
      const result = await getCases();

      setCases(
        Array.isArray(result) ? result : result.items || result.cases || [],
      );
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load cases."));
    } finally {
      setLoadingCases(false);
    }
  }

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleCreate(event) {
    event.preventDefault();

    if (!form.case_number.trim()) {
      toast.error("Case number is required.");

      return;
    }

    if (!form.title.trim()) {
      toast.error("Case title is required.");

      return;
    }

    setCreating(true);

    try {
      const createdCase = await createCase({
        case_number: form.case_number.trim(),

        title: form.title.trim(),

        description: form.description.trim() || null,
      });

      toast.success("Case created successfully.");

      selectCase(createdCase);

      setForm({
        case_number: "",
        title: "",
        description: "",
      });

      onCaseSelected(createdCase);
    } catch (error) {
      toast.error(getErrorMessage(error, "Case creation was unsuccessful."));
    } finally {
      setCreating(false);
    }
  }

  function handleOpen(caseData) {
    selectCase(caseData);

    toast.success("Case opened successfully.");

    onCaseSelected(caseData);
  }

  return (
    <Modal open={open} onClose={onClose} title="Create or open a case">
      <div className="mb-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
        <button
          type="button"
          onClick={() => setTab("create")}
          className={`
            rounded-lg px-3 py-2.5
            text-sm font-semibold
            ${
              tab === "create"
                ? "bg-white text-blue-700 shadow-sm"
                : "text-slate-500"
            }
          `}
        >
          Create New Case
        </button>

        <button
          type="button"
          onClick={() => setTab("existing")}
          className={`
            rounded-lg px-3 py-2.5
            text-sm font-semibold
            ${
              tab === "existing"
                ? "bg-white text-blue-700 shadow-sm"
                : "text-slate-500"
            }
          `}
        >
          Open Existing Case
        </button>
      </div>

      {tab === "create" ? (
        <form onSubmit={handleCreate} className="space-y-5">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Case Number
            </span>

            <input
              required
              type="text"
              name="case_number"
              value={form.case_number}
              onChange={handleChange}
              placeholder="For example: CASE-2026-001"
              className="
                mt-2 min-h-12 w-full
                rounded-xl border
                border-slate-300 px-4
                outline-none transition
                focus:border-blue-500
                focus:ring-4
                focus:ring-blue-100
              "
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Case Title
            </span>

            <input
              required
              type="text"
              name="title"
              value={form.title}
              onChange={handleChange}
              placeholder="Enter case title"
              className="
                mt-2 min-h-12 w-full
                rounded-xl border
                border-slate-300 px-4
                outline-none transition
                focus:border-blue-500
                focus:ring-4
                focus:ring-blue-100
              "
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Description
            </span>

            <textarea
              rows={4}
              name="description"
              value={form.description}
              onChange={handleChange}
              placeholder="Enter optional description"
              className="
                mt-2 w-full resize-none
                rounded-xl border
                border-slate-300
                px-4 py-3 outline-none
                transition
                focus:border-blue-500
                focus:ring-4
                focus:ring-blue-100
              "
            />
          </label>

          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>

            <Button type="submit" loading={creating}>
              Create Case
            </Button>
          </div>
        </form>
      ) : loadingCases ? (
        <LoadingSpinner text="Loading cases..." />
      ) : cases.length === 0 ? (
        <EmptyState
          title="No existing cases"
          description="Create your first case to begin uploading evidence."
        />
      ) : (
        <div className="grid max-h-[55vh] gap-4 overflow-y-auto pr-1 sm:grid-cols-2">
          {cases.map((caseData) => (
            <CaseCard
              key={caseData.id}
              caseData={caseData}
              onOpen={handleOpen}
            />
          ))}
        </div>
      )}
    </Modal>
  );
}
