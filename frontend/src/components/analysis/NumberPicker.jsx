import { Check, Search } from "lucide-react";

import { useEffect, useState } from "react";

import { toast } from "react-toastify";

import { getNumbers } from "../../api/analysisApi";

import { useCase } from "../../context/CaseContext";

import { getErrorMessage } from "../../utils/errorMessage";

export default function NumberPicker({ selectedNumber, onSelect }) {
  const { selectedCase, selectedEvidence } = useCase();

  const [search, setSearch] = useState("");

  const [numbers, setNumbers] = useState([]);

  const [loading, setLoading] = useState(false);

  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (selectedCase?.id && selectedEvidence?.id) {
      loadNumbers("");
    }
  }, [selectedCase?.id, selectedEvidence?.id]);

  async function loadNumbers(searchText) {
    if (!selectedCase || !selectedEvidence) {
      return;
    }

    setLoading(true);

    try {
      const result = await getNumbers(selectedCase.id, selectedEvidence.id, {
        search: searchText || undefined,
        offset: 0,
        limit: 100,
      });

      setNumbers(result.numbers || []);
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load phone numbers."));
    } finally {
      setLoading(false);
    }
  }

  function handleSearchChange(event) {
    const value = event.target.value;

    setSearch(value);
    setOpen(true);

    window.clearTimeout(window.numberSearchTimeout);

    window.numberSearchTimeout = window.setTimeout(() => {
      loadNumbers(value.trim());
    }, 350);
  }

  function handleSelection(number) {
    onSelect(number.phone_number);

    setSearch(number.phone_number);

    setOpen(false);
  }

  return (
    <div className="relative">
      <div className="relative">
        <Search
          size={18}
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
        />

        <input
          type="text"
          value={search}
          onFocus={() => setOpen(true)}
          onChange={handleSearchChange}
          placeholder="Search or select a number"
          className="min-h-12 w-full rounded-xl border border-slate-300 bg-white pl-11 pr-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        />
      </div>

      {open && (
        <div className="absolute left-0 right-0 z-30 mt-2 max-h-80 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
          {loading ? (
            <p className="px-3 py-5 text-center text-sm text-slate-500">
              Loading numbers...
            </p>
          ) : numbers.length === 0 ? (
            <p className="px-3 py-5 text-center text-sm text-slate-500">
              No matching numbers found.
            </p>
          ) : (
            numbers.map((number) => {
              const active = selectedNumber === number.phone_number;

              return (
                <button
                  key={number.phone_number}
                  type="button"
                  onClick={() => handleSelection(number)}
                  className={`
                    flex w-full
                    items-center
                    justify-between
                    rounded-lg px-3 py-3
                    text-left transition
                    ${active ? "bg-blue-50 text-blue-700" : "hover:bg-slate-50"}
                  `}
                >
                  <div>
                    <p className="font-semibold">{number.phone_number}</p>

                    <p className="mt-1 text-xs text-slate-500">
                      {number.total_records} records · {number.outgoing_records}{" "}
                      outgoing · {number.incoming_records} incoming
                    </p>
                  </div>

                  {active && <Check size={18} />}
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
