import { ArrowDown, Smartphone } from "lucide-react";

import {
  formatVisualizationDateTime,
  getDeviceChangeArray,
} from "../../utils/visualizationHelpers";

export default function DeviceTimeline({ result }) {
  const changeEvents = getDeviceChangeArray(result);

  const devices = Array.isArray(result?.devices) ? result.devices : [];

  if (changeEvents.length === 0 && devices.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Smartphone size={34} className="mx-auto text-slate-300" />

        <h3 className="mt-4 font-bold text-slate-900">
          No device history available
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          Run Device History using a phone number to display its IMEI timeline.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold text-slate-950">
        Device-change timeline
      </h2>

      <p className="mt-1 text-sm text-slate-500">
        Chronological device associations found in the selected evidence.
      </p>

      {devices.length > 0 && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {devices.map((device, index) => (
            <article
              key={`${device.imei}-${index}`}
              className="rounded-xl border border-violet-100 bg-violet-50/50 p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-violet-500">
                Device {index + 1}
              </p>

              <p className="mt-2 break-all font-bold text-slate-900">
                {device.imei}
              </p>

              <p className="mt-2 text-sm text-slate-600">
                Records:{" "}
                <span className="font-semibold">
                  {device.record_count ?? 0}
                </span>
              </p>

              <p className="mt-1 text-xs text-slate-500">
                First: {formatVisualizationDateTime(device.first_seen)}
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Last: {formatVisualizationDateTime(device.last_seen)}
              </p>
            </article>
          ))}
        </div>
      )}

      {changeEvents.length > 0 && (
        <div className="relative mt-7">
          <div className="absolute bottom-4 left-[19px] top-4 w-0.5 bg-violet-200" />

          <div className="space-y-5">
            {changeEvents.map((event, index) => (
              <article
                key={`${event.change_datetime}-${index}`}
                className="relative pl-14"
              >
                <span className="absolute left-0 top-1 flex h-10 w-10 items-center justify-center rounded-full border-4 border-white bg-violet-600 text-white shadow-sm">
                  <Smartphone size={17} />
                </span>

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-bold text-slate-950">
                    Device changed
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    {formatVisualizationDateTime(event.change_datetime)}
                  </p>

                  <div className="mt-4 flex flex-col items-start gap-2 sm:flex-row sm:items-center">
                    <span className="break-all rounded-lg bg-white px-3 py-2 text-sm font-semibold text-slate-700">
                      {event.previous_imei || "Unknown previous IMEI"}
                    </span>

                    <ArrowDown
                      size={18}
                      className="text-violet-500 sm:-rotate-90"
                    />

                    <span className="break-all rounded-lg bg-violet-100 px-3 py-2 text-sm font-semibold text-violet-800">
                      {event.new_imei || "Unknown new IMEI"}
                    </span>
                  </div>

                  <p className="mt-3 text-xs text-slate-500">
                    Evidence ID: {event.evidence_id ?? "—"} · Source row:{" "}
                    {event.source_row ?? "—"}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
