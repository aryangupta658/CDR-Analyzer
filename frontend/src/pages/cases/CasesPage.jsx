import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router";

import { getCases } from "../../api/caseApi";

import CaseCard from "../../components/cases/CaseCard";
import CaseSelectionModal from "../../components/cases/CaseSelectionModal";
import Button from "../../components/common/Button";
import EmptyState from "../../components/common/EmptyState";
import LoadingSpinner from "../../components/common/LoadingSpinner";
import PageHeader from "../../components/common/PageHeader";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

export default function CasesPage() {
  const [cases, setCases] = useState([]);

  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(true);

  const navigate = useNavigate();
  const { selectCase } = useCase();

  useEffect(() => {
    loadCases();
  }, []);

  async function loadCases() {
    try {
      const result = await getCases();

      setCases(
        Array.isArray(result) ? result : result.items || result.cases || [],
      );
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load cases."));
    } finally {
      setLoading(false);
    }
  }

  function openCase(caseData) {
    selectCase(caseData);

    navigate(`/app/cases/${caseData.id}/evidence`);
  }

  function handleCaseSelected(caseData) {
    setModalOpen(false);

    navigate(`/app/cases/${caseData.id}/evidence`);
  }

  return (
    <>
      <PageHeader
        title="Cases"
        description="Create a case or continue an existing investigation."
        action={
          <Button onClick={() => setModalOpen(true)}>
            <Plus size={17} />
            Create / Open Case
          </Button>
        }
      />

      {loading ? (
        <LoadingSpinner text="Loading cases..." />
      ) : cases.length === 0 ? (
        <EmptyState
          title="No cases yet"
          description="Create your first case to upload and analyse a CDR file."
          action={
            <Button onClick={() => setModalOpen(true)}>Create Case</Button>
          }
        />
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {cases.map((caseData) => (
            <CaseCard key={caseData.id} caseData={caseData} onOpen={openCase} />
          ))}
        </div>
      )}

      <CaseSelectionModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCaseSelected={handleCaseSelected}
      />
    </>
  );
}
