import { ArrowDown, Clock3, PhoneCall, RadioTower } from "lucide-react";

import {
  formatVisualizationDateTime,
  formatVisualizationDuration,
  getIncidentEventArray,
} from "../../utils/visualizationHelpers";

function getPhaseConfiguration(phase) {
  if (phase === "before_incident") {
    return {
      title: "Before incident",
      colour: "bg-blue-600 text-white",
      border: "border-blue-200",
      panel: "bg-blue-50/50",
    };
  }

  if (phase === "at_incident") {
    return {
      title: "At incident",
      colour: "bg-orange-500 text-white",
      border: "border-orange-200",
      panel: "bg-orange-50/60",
    };
  }

  return {
    title: "After incident",
    colour: "bg-emerald-600 text-white",
    border: "border-emerald-200",
    panel: "bg-emerald-50/50",
  };
}

export default function IncidentTimeline({ result }) {
  const events = getIncidentEventArray(result);

  if (events.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Clock3 size={34} className="mx-auto text-slate-300" />

        <h3 className="mt-4 font-bold text-slate-900">
          No incident events found
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          Increase the time window or choose an incident time closer to the CDR
          activity.
        </p>
      </section>
    );
  }

  const sortedEvents = [...events].sort((first, second) => {
    const firstDate = new Date(
      first.start_datetime || first.event_datetime,
    ).getTime();

    const secondDate = new Date(
      second.start_datetime || second.event_datetime,
    ).getTime();

    return firstDate - secondDate;
  });

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold text-slate-950">
        Incident activity timeline
      </h2>

      <p className="mt-1 text-sm text-slate-500">
        Events are ordered relative to the selected incident time.
      </p>

      <div className="relative mt-7">
        <div className="absolute bottom-5 left-[19px] top-5 w-0.5 bg-slate-200" />

        <div className="space-y-5">
          {sortedEvents.map((event, index) => {
            const configuration = getPhaseConfiguration(event.phase);

            const relativeSeconds = Number(event.relative_seconds);

            const relativeText = Number.isFinite(relativeSeconds)
              ? relativeSeconds === 0
                ? "Exactly at incident time"
                : relativeSeconds < 0
                  ? `${Math.abs(relativeSeconds)} seconds before`
                  : `${relativeSeconds} seconds after`
              : "Relative time unavailable";

            return (
              <article
                key={event.record_id || `${event.start_datetime}-${index}`}
                className="relative pl-14"
              >
                <span
                  className={`
                      absolute left-0 top-1
                      flex h-10 w-10
                      items-center justify-center
                      rounded-full border-4
                      border-white shadow-sm
                      ${configuration.colour}
                    `}
                >
                  {event.cell_id ? (
                    <RadioTower size={16} />
                  ) : (
                    <PhoneCall size={16} />
                  )}
                </span>

                <div
                  className={`
                      rounded-xl border p-4
                      ${configuration.border}
                      ${configuration.panel}
                    `}
                >
                  <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                    <div>
                      <p className="font-bold text-slate-950">
                        {configuration.title}
                      </p>

                      <p className="mt-1 text-xs font-semibold text-slate-500">
                        {relativeText}
                      </p>
                    </div>

                    <span className="text-xs font-medium text-slate-500">
                      {formatVisualizationDateTime(
                        event.start_datetime || event.event_datetime,
                      )}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-400">
                        Caller
                      </p>

                      <p className="mt-1 font-semibold text-slate-800">
                        {event.caller_number || "—"}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-400">
                        Receiver
                      </p>

                      <p className="mt-1 font-semibold text-slate-800">
                        {event.receiver_number || "—"}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-400">
                        Event
                      </p>

                      <p className="mt-1 font-semibold text-slate-800">
                        {event.event_type || "—"}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-400">
                        Duration
                      </p>

                      <p className="mt-1 font-semibold text-slate-800">
                        {formatVisualizationDuration(event.duration_seconds)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs">
                    {event.cell_id && (
                      <span className="rounded-full bg-white px-3 py-1.5 font-semibold text-slate-700">
                        Cell: {event.cell_id}
                      </span>
                    )}

                    {event.imei && (
                      <span className="rounded-full bg-white px-3 py-1.5 font-semibold text-slate-700">
                        IMEI: {event.imei}
                      </span>
                    )}

                    {event.imsi && (
                      <span className="rounded-full bg-white px-3 py-1.5 font-semibold text-slate-700">
                        IMSI: {event.imsi}
                      </span>
                    )}
                  </div>
                </div>

                {index < sortedEvents.length - 1 && (
                  <ArrowDown
                    size={14}
                    className="absolute -bottom-4 left-[13px] text-slate-300"
                  />
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
