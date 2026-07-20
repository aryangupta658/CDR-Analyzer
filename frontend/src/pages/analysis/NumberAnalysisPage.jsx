import {
  Activity,
  Clock3,
  MessageSquareText,
  Network,
  PhoneIncoming,
  PhoneOutgoing,
  Search,
  Share2,
  Smartphone,
  TriangleAlert,
  Users,
} from "lucide-react";

import { useEffect, useState } from "react";

import { toast } from "react-toastify";

import {
  getCallsByDate,
  getCallsByHour,
  getContactNetwork,
  getContactTimeline,
  getNumberAnalysis,
  getTopContacts,
} from "../../api/analysisApi";

import { getCommonContacts } from "../../api/forensicApi";
import { getNumberPatterns } from "../../api/fraudApi";

import {
  DailyActivityChart,
  HourlyActivityChart,
} from "../../components/analysis/ActivityCharts";

import AnalysisTabs from "../../components/analysis/AnalysisTabs";
import DataTable from "../../components/analysis/DataTable";
import EvidenceContextCard from "../../components/analysis/EvidenceContextCard";
import MetricCard from "../../components/analysis/MetricCard";
import NumberPicker from "../../components/analysis/NumberPicker";

import Button from "../../components/common/Button";
import LoadingSpinner from "../../components/common/LoadingSpinner";
import PageHeader from "../../components/common/PageHeader";

import AnalysisResult from "../../components/results/AnalysisResult";

import SigmaCommunicationGraph from "../../components/visualizations/SigmaCommunicationGraph";

import { useCase } from "../../context/CaseContext";
import { getErrorMessage } from "../../utils/errorMessage";

function formatDuration(seconds) {
  const totalSeconds = Number(seconds) || 0;

  const hours = Math.floor(totalSeconds / 3600);

  const minutes = Math.floor((totalSeconds % 3600) / 60);

  const remainingSeconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ` + `${remainingSeconds}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ` + `${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}

function formatDateTime(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN");
}

function formatCoordinate(latitude, longitude) {
  if (latitude === null || latitude === undefined) {
    return "—";
  }

  if (longitude === null || longitude === undefined) {
    return String(latitude);
  }

  return `${latitude}, ${longitude}`;
}

function TimelineDetail({ label, value }) {
  const displayValue =
    value === null || value === undefined || value === "" ? "—" : value;

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>

      <p className="mt-1 break-words text-sm font-medium text-slate-800">
        {String(displayValue)}
      </p>
    </div>
  );
}

function IdentityChips({ values, emptyText }) {
  if (!Array.isArray(values) || values.length === 0) {
    return <p className="mt-3 text-sm text-slate-500">{emptyText}</p>;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
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

export default function NumberAnalysisPage() {
  const { selectedCase, selectedEvidence } = useCase();

  const [activeTab, setActiveTab] = useState("profile");

  const [phoneNumber, setPhoneNumber] = useState("");

  const [profile, setProfile] = useState(null);

  const [incidentDateTime, setIncidentDateTime] = useState("");

  const [incidentCellIds, setIncidentCellIds] = useState("");

  const [patternResult, setPatternResult] = useState(null);

  const [patternLoading, setPatternLoading] = useState(false);

  const [topContacts, setTopContacts] = useState([]);

  const [timelineContact, setTimelineContact] = useState("");

  const [contactTimeline, setContactTimeline] = useState(null);

  const [timelineLoading, setTimelineLoading] = useState(false);

  const [hourlyActivity, setHourlyActivity] = useState([]);

  const [dailyActivity, setDailyActivity] = useState([]);

  const [commonTargets, setCommonTargets] = useState("");

  const [commonResult, setCommonResult] = useState(null);

  const [contactNetwork, setContactNetwork] = useState(null);

  const [networkLoading, setNetworkLoading] = useState(false);

  const [loading, setLoading] = useState(false);

  const [activityLoading, setActivityLoading] = useState(false);

  const tabs = [
    {
      id: "profile",
      label: "Number Profile",
      icon: Search,
    },
    {
      id: "contacts",
      label: "Top Contacts",
      icon: Users,
    },
    {
      id: "network",
      label: "Contact Network",
      icon: Share2,
    },
    {
      id: "activity",
      label: "Activity Charts",
      icon: Activity,
    },
    {
      id: "patterns",
      label: "Patterns",
      icon: TriangleAlert,
    },
    {
      id: "common",
      label: "Common Contacts",
      icon: Network,
    },
  ];

  useEffect(() => {
    setPhoneNumber("");
    setIncidentDateTime("");
    setIncidentCellIds("");
    setProfile(null);
    setPatternResult(null);
    setTopContacts([]);
    setTimelineContact("");
    setContactTimeline(null);
    setHourlyActivity([]);
    setDailyActivity([]);
    setCommonTargets("");
    setCommonResult(null);
    setContactNetwork(null);
    setActiveTab("profile");
  }, [selectedEvidence?.id]);

  async function runNumberAnalysis() {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence.");

      return;
    }

    const cleanedNumber = phoneNumber.trim();

    if (!cleanedNumber) {
      toast.error("Select or enter a phone number.");

      return;
    }

    setLoading(true);
    setPatternLoading(true);
    setActivityLoading(true);
    setProfile(null);
    setPatternResult(null);
    setTopContacts([]);
    setTimelineContact("");
    setContactTimeline(null);
    setContactNetwork(null);
    setHourlyActivity([]);
    setDailyActivity([]);

    try {
      const [
        profileResult,
        contactResult,
        patternData,
        hourlyResult,
        dailyResult,
      ] = await Promise.all([
        getNumberAnalysis(selectedCase.id, selectedEvidence.id, cleanedNumber),

        getTopContacts(selectedCase.id, selectedEvidence.id, cleanedNumber, 20),

        getNumberPatterns(
          selectedCase.id,
          selectedEvidence.id,
          cleanedNumber,
          incidentDateTime,
          incidentCellIds,
        ),

        getCallsByHour(selectedCase.id, selectedEvidence.id, cleanedNumber),

        getCallsByDate(selectedCase.id, selectedEvidence.id, cleanedNumber),
      ]);

      setProfile(profileResult);

      setTopContacts(contactResult.contacts || []);

      setPatternResult(patternData);

      setHourlyActivity(hourlyResult.activity || []);
      setDailyActivity(dailyResult.activity || []);

      setActiveTab("profile");

      toast.success("Number analysis completed.");
    } catch (error) {
      setProfile(null);
      setPatternResult(null);
      setTopContacts([]);
      setTimelineContact("");
      setContactTimeline(null);
      setHourlyActivity([]);
      setDailyActivity([]);

      toast.error(getErrorMessage(error, "Number analysis failed."));
    } finally {
      setLoading(false);
      setPatternLoading(false);
      setActivityLoading(false);
    }
  }

  async function loadContactTimeline(contactNumber) {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence.");

      return;
    }

    const cleanedNumber = phoneNumber.trim();
    const cleanedContact = String(contactNumber || "").trim();

    if (!cleanedNumber) {
      toast.error("Select and analyse a phone number first.");

      return;
    }

    if (!cleanedContact) {
      toast.error("A contact number is required.");

      return;
    }

    setTimelineContact(cleanedContact);
    setContactTimeline(null);
    setTimelineLoading(true);

    try {
      const result = await getContactTimeline(
        selectedCase.id,
        selectedEvidence.id,
        cleanedNumber,
        cleanedContact,
      );

      setContactTimeline(result);
    } catch (error) {
      setTimelineContact("");
      setContactTimeline(null);

      toast.error(
        getErrorMessage(error, "Could not load the contact timeline."),
      );
    } finally {
      setTimelineLoading(false);
    }
  }

  function closeContactTimeline() {
    setTimelineContact("");
    setContactTimeline(null);
  }

  async function loadContactNetwork() {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence.");

      return;
    }

    const cleanedNumber = phoneNumber.trim();

    if (!cleanedNumber) {
      toast.error("Select and analyse a phone number first.");

      return;
    }

    setNetworkLoading(true);
    setContactNetwork(null);

    try {
      const data = await getContactNetwork(
        selectedCase.id,
        selectedEvidence.id,
        cleanedNumber,
      );

      setContactNetwork(data);

      if (Number(data.node_count) === 0) {
        toast.info(
          "No valid caller-and-receiver relationship was found in this evidence.",
        );
      } else {
        toast.success("Full-evidence communication graph loaded.");
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load contact network."));
    } finally {
      setNetworkLoading(false);
    }
  }

  async function runCommonContacts() {
    if (!selectedCase || !selectedEvidence) {
      toast.error("Select a case and imported evidence.");

      return;
    }

    const targetNumbers = commonTargets
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    if (targetNumbers.length < 2) {
      toast.error("Enter at least two comma-separated target numbers.");

      return;
    }

    setLoading(true);
    setCommonResult(null);

    try {
      const result = await getCommonContacts(
        selectedCase.id,
        selectedEvidence.id,
        {
          target_numbers: targetNumbers,

          minimum_common_targets: 2,

          limit: 100,
        },
      );

      setCommonResult(result);

      toast.success("Common-contact analysis completed.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Common-contact analysis failed."));
    } finally {
      setLoading(false);
    }
  }

  function handleNumberSelection(selectedNumber) {
    setPhoneNumber(selectedNumber);

    setProfile(null);
    setPatternResult(null);
    setTopContacts([]);
    setTimelineContact("");
    setContactTimeline(null);
    setContactNetwork(null);
    setCommonResult(null);
    setActiveTab("profile");
  }

  function clearNumberAnalysis() {
    setPhoneNumber("");
    setIncidentDateTime("");
    setIncidentCellIds("");
    setProfile(null);
    setPatternResult(null);
    setTopContacts([]);
    setTimelineContact("");
    setContactTimeline(null);
    setContactNetwork(null);
    setCommonTargets("");
    setCommonResult(null);
    setActiveTab("profile");
  }

  const profileMetrics = profile
    ? [
        {
          label: "Total Records",
          value: profile.total_records ?? 0,
          icon: Activity,
        },
        {
          label: "Outgoing Records",
          value: profile.outgoing_records ?? 0,
          icon: PhoneOutgoing,
        },
        {
          label: "Incoming Records",
          value: profile.incoming_records ?? 0,
          icon: PhoneIncoming,
        },
        {
          label: "Unique Contacts",
          value: profile.unique_contacts ?? 0,
          icon: Users,
        },
        {
          label: "SMS Sent",
          value: profile.sms_sent ?? 0,
          icon: MessageSquareText,
        },
        {
          label: "SMS Received",
          value: profile.sms_received ?? 0,
          icon: MessageSquareText,
        },
        {
          label: "Unique IMEIs",
          value: profile.unique_imeis ?? 0,
          icon: Smartphone,
        },
        {
          label: "Total Duration",
          value: formatDuration(profile.total_duration_seconds),
          icon: Clock3,
        },
      ]
    : [];

  const topContactColumns = [
    {
      key: "contact_number",
      label: "Contact Number",

      render: (value, row) => (
        <button
          type="button"
          onClick={() => loadContactTimeline(row.contact_number)}
          disabled={timelineLoading}
          className="font-semibold text-blue-700 transition hover:text-blue-900 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
        >
          {value}
        </button>
      ),
    },
    {
      key: "total_records",
      label: "Records",
    },
    {
      key: "outgoing_records",
      label: "Outgoing",
    },
    {
      key: "incoming_records",
      label: "Incoming",
    },
    {
      key: "total_duration_seconds",
      label: "Duration",

      render: (value) => formatDuration(value),
    },
    {
      key: "first_contact",
      label: "First Contact",

      render: (value) => formatDateTime(value),
    },
    {
      key: "last_contact",
      label: "Last Contact",

      render: (value) => formatDateTime(value),
    },
    {
      key: "timeline",
      label: "Contact Timeline",

      render: (_value, row) => (
        <button
          type="button"
          onClick={() => loadContactTimeline(row.contact_number)}
          disabled={timelineLoading}
          className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          View {row.total_records} records
        </button>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Number Analysis"
        description="Examine phone-number activity, contacts and multi-level communication relationships."
      />

      <EvidenceContextCard />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <Search size={21} />
          </span>

          <div>
            <h2 className="font-bold text-slate-950">Select a number</h2>

            <p className="mt-1 text-sm text-slate-500">
              Search numbers found in the selected evidence and run the number
              analysis.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto]">
          <NumberPicker
            selectedNumber={phoneNumber}
            onSelect={handleNumberSelection}
          />

          <Button
            loading={loading}
            disabled={loading || !phoneNumber.trim()}
            onClick={runNumberAnalysis}
          >
            <Search size={17} />
            Analyse Number
          </Button>
        </div>

        <div className="mt-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Incident date and time (optional)
            </span>

            <input
              type="datetime-local"
              value={incidentDateTime}
              onChange={(event) => {
                setIncidentDateTime(event.target.value);
                setPatternResult(null);
              }}
              className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </label>

          <p className="mt-2 text-xs text-slate-500">
            Leave empty for short-window and full-evidence patterns. Select a
            date and time to also apply incident comparison rules.
          </p>
        </div>

        {incidentDateTime && (
          <div className="mt-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">
                Incident cell IDs (optional)
              </span>

              <input
                type="text"
                value={incidentCellIds}
                onChange={(event) => {
                  setIncidentCellIds(event.target.value);
                  setPatternResult(null);
                }}
                placeholder="CGI00426, CGI00427"
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </label>

            <p className="mt-2 text-xs text-slate-500">
              Enter comma-separated CGI or cell IDs to check incident-tower
              presence. Leave empty when only incident-time rules are required.
            </p>
          </div>
        )}

        {phoneNumber && (
          <div className="mt-4 flex flex-col justify-between gap-3 rounded-xl bg-slate-50 p-4 sm:flex-row sm:items-center">
            <p className="text-sm text-slate-500">
              Selected number:{" "}
              <span className="font-semibold text-blue-700">{phoneNumber}</span>
            </p>

            <button
              type="button"
              onClick={clearNumberAnalysis}
              disabled={loading || networkLoading}
              className="self-start text-sm font-semibold text-slate-500 transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50 sm:self-auto"
            >
              Clear number and results
            </button>
          </div>
        )}
      </section>

      <div className="mt-6">
        <AnalysisTabs
          tabs={tabs}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {activeTab === "profile" && (
        <section className="mt-6">
          {!profile ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
              <Search size={36} className="mx-auto text-slate-300" />

              <h2 className="mt-4 font-bold text-slate-900">
                Select a number to begin
              </h2>

              <p className="mt-2 text-sm text-slate-500">
                Search for a number and click Analyse Number to view its
                profile.
              </p>
            </div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {profileMetrics.map((metric) => (
                  <MetricCard key={metric.label} {...metric} />
                ))}
              </div>

              <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="font-bold text-slate-950">Activity period</h2>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      First activity
                    </p>

                    <p className="mt-2 font-medium text-slate-800">
                      {formatDateTime(profile.first_activity)}
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Last activity
                    </p>

                    <p className="mt-2 font-medium text-slate-800">
                      {formatDateTime(profile.last_activity)}
                    </p>
                  </div>
                </div>
              </section>

              <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div>
                  <h2 className="font-bold text-slate-950">
                    Device and SIM identities linked with this number
                  </h2>

                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    These values are taken only from CDR rows where the selected
                    number is the target subscriber, so a contact's device is
                    not incorrectly assigned to this number.
                  </p>
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-slate-900">
                        IMEI values
                      </h3>

                      <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
                        {profile.unique_imeis ?? 0} unique
                      </span>
                    </div>

                    <IdentityChips
                      values={profile.imei_values}
                      emptyText="No IMEI value is linked with this number in the selected evidence."
                    />
                  </div>

                  <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-slate-900">
                        IMSI values
                      </h3>

                      <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
                        {profile.unique_imsis ?? 0} unique
                      </span>
                    </div>

                    <IdentityChips
                      values={profile.imsi_values}
                      emptyText="No IMSI value is linked with this number in the selected evidence."
                    />
                  </div>
                </div>
              </section>
            </>
          )}
        </section>
      )}

      {activeTab === "contacts" && (
        <section className="mt-6">
          <div className="mb-4">
            <h2 className="text-xl font-bold text-slate-950">Top contacts</h2>

            <p className="mt-1 text-sm text-slate-500">
              Direct contacts ordered by communication record count. Click a
              contact number or View Timeline to inspect every record exchanged
              with that contact.
            </p>
          </div>

          <DataTable
            columns={topContactColumns}
            rows={topContacts}
            emptyTitle="No contact information"
            emptyDescription="Select and analyse a phone number to view its strongest direct contacts."
          />

          {timelineLoading && (
            <div className="mt-5">
              <LoadingSpinner
                text={`Loading communication timeline for ${timelineContact}...`}
              />
            </div>
          )}

          {!timelineLoading && contactTimeline && (
            <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                <div>
                  <h3 className="text-lg font-bold text-slate-950">
                    Contact timeline
                  </h3>

                  <p className="mt-1 text-sm text-slate-500">
                    {contactTimeline.phone_number} and{" "}
                    {contactTimeline.contact_number} exchanged{" "}
                    {contactTimeline.total_records} communication records in the
                    selected evidence.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={closeContactTimeline}
                  className="self-start text-sm font-semibold text-slate-500 transition hover:text-red-600"
                >
                  Close timeline
                </button>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Total records
                  </p>
                  <p className="mt-2 text-xl font-bold text-slate-900">
                    {contactTimeline.total_records}
                  </p>
                </div>

                <div className="rounded-xl bg-blue-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
                    Outgoing
                  </p>
                  <p className="mt-2 text-xl font-bold text-blue-900">
                    {contactTimeline.outgoing_records}
                  </p>
                </div>

                <div className="rounded-xl bg-emerald-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
                    Incoming
                  </p>
                  <p className="mt-2 text-xl font-bold text-emerald-900">
                    {contactTimeline.incoming_records}
                  </p>
                </div>

                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Contact period
                  </p>
                  <p className="mt-2 text-sm font-semibold text-slate-800">
                    {formatDateTime(contactTimeline.first_contact)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    to {formatDateTime(contactTimeline.last_contact)}
                  </p>
                </div>
              </div>

              <div className="mt-6 space-y-4 border-l-2 border-slate-200 pl-5">
                {contactTimeline.records.map((record, recordIndex) => (
                  <article
                    key={record.record_id}
                    className="relative rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <span className="absolute -left-[1.72rem] top-6 h-3.5 w-3.5 rounded-full border-2 border-white bg-blue-600 shadow" />

                    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Communication {recordIndex + 1}
                        </p>

                        <h4 className="mt-1 font-bold text-slate-950">
                          {formatDateTime(record.start_datetime)}
                        </h4>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${
                            record.direction === "outgoing"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {record.direction}
                        </span>

                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase text-slate-700">
                          {record.event_type ||
                            record.connection_type ||
                            "Record"}
                        </span>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      <TimelineDetail
                        label="Caller"
                        value={record.caller_number}
                      />
                      <TimelineDetail
                        label="Receiver"
                        value={record.receiver_number}
                      />
                      <TimelineDetail
                        label="Duration"
                        value={formatDuration(record.duration_seconds)}
                      />
                      <TimelineDetail
                        label="Source row"
                        value={record.source_row}
                      />

                      <TimelineDetail
                        label="Call type"
                        value={record.call_type}
                      />
                      <TimelineDetail
                        label="Communication type"
                        value={record.connection_type}
                      />
                      <TimelineDetail
                        label="Target number"
                        value={record.target_number}
                      />
                      <TimelineDetail
                        label="B-party number"
                        value={record.b_party_number}
                      />

                      <TimelineDetail label="IMEI" value={record.imei} />
                      <TimelineDetail label="IMSI" value={record.imsi} />
                      <TimelineDetail
                        label="LRN number"
                        value={record.lrn_number}
                      />
                      <TimelineDetail
                        label="LRN provider"
                        value={record.lrn_translation}
                      />

                      <TimelineDetail
                        label="First CGI"
                        value={record.first_cell_global_id}
                      />
                      <TimelineDetail
                        label="First coordinates"
                        value={formatCoordinate(
                          record.first_latitude,
                          record.first_longitude,
                        )}
                      />
                      <TimelineDetail
                        label="Last CGI"
                        value={record.last_cell_global_id}
                      />
                      <TimelineDetail
                        label="Last coordinates"
                        value={formatCoordinate(
                          record.last_latitude,
                          record.last_longitude,
                        )}
                      />

                      <TimelineDetail
                        label="SMSC number"
                        value={record.sms_centre_number}
                      />
                      <TimelineDetail
                        label="Call forwarding"
                        value={record.call_forwarding_number}
                      />
                      <TimelineDetail
                        label="Roaming"
                        value={
                          record.roaming === true
                            ? "Yes"
                            : record.roaming === false
                              ? "No"
                              : "—"
                        }
                      />
                      <TimelineDetail
                        label="Roaming network"
                        value={record.roaming_network_circle}
                      />

                      <TimelineDetail
                        label="MSC ID"
                        value={record.switch_msc_id}
                      />
                      <TimelineDetail label="IN TG" value={record.in_tg} />
                      <TimelineDetail label="OUT TG" value={record.out_tg} />
                      <TimelineDetail
                        label="PAN number"
                        value={record.pan_no}
                      />
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}
        </section>
      )}

      {activeTab === "network" && (
        <section className="mt-6">
          <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
              <div className="max-w-3xl">
                <div className="flex items-start gap-3">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <Share2 size={21} />
                  </span>

                  <div>
                    <h2 className="font-bold text-slate-950">
                      Complete CDR communication graph
                    </h2>

                    <p className="mt-1 text-sm leading-6 text-slate-500">
                      This graph uses every valid caller-and-receiver
                      relationship from the selected evidence. The analysed
                      number is highlighted, but the graph is not restricted to
                      its contacts and does not use Level 1, Level 2 or Level 3.
                    </p>
                  </div>
                </div>
              </div>

              <Button
                loading={networkLoading}
                disabled={networkLoading || !phoneNumber.trim()}
                onClick={loadContactNetwork}
              >
                <Share2 size={17} />
                Load Full Graph
              </Button>
            </div>

            {phoneNumber && (
              <p className="mt-4 text-sm text-slate-500">
                Highlighted number:{" "}
                <span className="font-semibold text-blue-700">
                  {phoneNumber}
                </span>
              </p>
            )}
          </div>

          {networkLoading ? (
            <LoadingSpinner text="Building the full communication graph..." />
          ) : contactNetwork ? (
            <SigmaCommunicationGraph network={contactNetwork} />
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
              <Share2 size={38} className="mx-auto text-slate-300" />

              <h3 className="mt-4 font-bold text-slate-900">
                Load the complete communication graph
              </h3>

              <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
                Analyse a number and click Load Full Graph. Every number and
                relationship available in the selected CDR evidence will be
                shown, while the analysed number remains highlighted for
                orientation.
              </p>
            </div>
          )}
        </section>
      )}

      {activeTab === "activity" && (
        <section className="mt-6">
          {activityLoading ? (
            <LoadingSpinner text="Loading activity charts..." />
          ) : (
            <div className="grid gap-5 xl:grid-cols-2">
              <HourlyActivityChart
                activity={hourlyActivity}
                phoneNumber={profile?.phone_number || phoneNumber.trim()}
              />

              <DailyActivityChart
                activity={dailyActivity}
                phoneNumber={profile?.phone_number || phoneNumber.trim()}
              />
            </div>
          )}
        </section>
      )}

      {activeTab === "patterns" && (
        <section className="mt-6">
          <div className="mb-4">
            <h2 className="text-xl font-bold text-slate-950">
              Detected communication patterns
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Short-window and full-evidence patterns are always checked.
              Incident patterns are included only when an incident date and time
              was selected before analysing the number.
            </p>
          </div>

          {patternLoading ? (
            <LoadingSpinner text="Checking communication patterns..." />
          ) : !patternResult ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
              <TriangleAlert size={38} className="mx-auto text-slate-300" />

              <h3 className="mt-4 font-bold text-slate-900">
                Analyse a number to view patterns
              </h3>

              <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
                The analyzer displays only explainable behavioural and technical
                observations found in the selected evidence.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  ["Total patterns", patternResult.total_patterns],
                  ["Short window", patternResult.short_window_patterns],
                  ["Full evidence", patternResult.full_evidence_patterns],
                  ["Incident", patternResult.incident_patterns],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <p className="text-sm font-medium text-slate-500">
                      {label}
                    </p>

                    <p className="mt-2 text-3xl font-bold text-slate-900">
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                {patternResult.disclaimer}
              </div>

              {patternResult.patterns.length === 0 ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
                  <TriangleAlert size={38} className="mx-auto text-slate-300" />

                  <p className="mt-3 font-semibold text-slate-700">
                    No configured pattern was detected
                  </p>
                </div>
              ) : (
                patternResult.patterns.map((pattern) => (
                  <article
                    key={pattern.pattern_id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h3 className="font-bold text-slate-900">
                          {pattern.title}
                        </h3>

                        <p className="mt-2 text-sm text-slate-600">
                          {pattern.description}
                        </p>
                      </div>

                      <div className="rounded-xl bg-slate-100 px-4 py-2 text-center">
                        <p className="text-xs uppercase tracking-wide text-slate-500">
                          Observed
                        </p>

                        <p className="mt-1 font-bold text-slate-900">
                          {String(pattern.observed_value)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <div>
                        <p className="text-xs font-semibold uppercase text-slate-400">
                          Scope
                        </p>

                        <p className="mt-1 font-medium text-slate-800">
                          {String(pattern.scope).replaceAll("_", " ")}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase text-slate-400">
                          Comparison
                        </p>

                        <p className="mt-1 font-medium text-slate-800">
                          {pattern.comparison_value || "Not required"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs font-semibold uppercase text-slate-400">
                          Source records
                        </p>

                        <p className="mt-1 font-medium text-slate-800">
                          {pattern.source_record_ids.length}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 rounded-xl bg-slate-50 p-4">
                      <p className="text-sm text-slate-700">
                        {pattern.explanation}
                      </p>

                      <p className="mt-2 text-xs text-slate-500">
                        {formatDateTime(pattern.window_start)} to{" "}
                        {formatDateTime(pattern.window_end)}
                      </p>
                    </div>
                  </article>
                ))
              )}
            </div>
          )}
        </section>
      )}

      {activeTab === "common" && (
        <section className="mt-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-600">
                <Network size={21} />
              </span>

              <div>
                <h2 className="font-bold text-slate-950">
                  Common-contact analysis
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Enter two or more comma-separated target numbers to find
                  contacts shared by them.
                </p>
              </div>
            </div>

            <input
              type="text"
              value={commonTargets}
              onChange={(event) => setCommonTargets(event.target.value)}
              placeholder="9876500001, 9876500002"
              className="mt-5 min-h-12 w-full rounded-xl border border-slate-300 px-4 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />

            <Button
              className="mt-4"
              variant="orange"
              loading={loading}
              disabled={loading || !commonTargets.trim()}
              onClick={runCommonContacts}
            >
              <Users size={17} />
              Find Common Contacts
            </Button>
          </div>

          <AnalysisResult data={commonResult} title="Common Contact Analysis" />
        </section>
      )}
    </>
  );
}
