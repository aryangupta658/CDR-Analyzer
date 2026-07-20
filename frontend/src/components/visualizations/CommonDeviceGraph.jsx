import { Smartphone, Users } from "lucide-react";

import { getCommonDeviceArray } from "../../utils/visualizationHelpers";

export default function CommonDeviceGraph({ result }) {
  const devices = getCommonDeviceArray(result);

  if (devices.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Smartphone size={34} className="mx-auto text-slate-300" />

        <h3 className="mt-4 font-bold text-slate-900">
          No common devices found
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          No IMEI is associated with two or more numbers in this evidence.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-5">
      {devices.map((device, deviceIndex) => {
        const numbers = device.associated_numbers || device.phone_numbers || [];

        return (
          <article
            key={`${device.imei}-${deviceIndex}`}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-violet-500">
                  Shared device
                </p>

                <h3 className="mt-2 break-all text-lg font-bold text-slate-950">
                  IMEI {device.imei}
                </h3>
              </div>

              <span className="inline-flex items-center gap-2 self-start rounded-full bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700">
                <Users size={14} />
                {device.associated_number_count || numbers.length} numbers
              </span>
            </div>

            <div className="mt-6 flex flex-col items-center">
              <span className="flex h-20 w-20 items-center justify-center rounded-full bg-violet-600 text-white shadow-lg shadow-violet-200">
                <Smartphone size={34} />
              </span>

              <div className="h-8 w-0.5 bg-violet-200" />

              <div className="flex max-w-4xl flex-wrap justify-center gap-3">
                {numbers.map((number) => (
                  <span
                    key={number}
                    className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-bold text-blue-700"
                  >
                    {number}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Total records
                </p>

                <p className="mt-2 text-xl font-bold text-slate-900">
                  {device.total_records ?? 0}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Related IMSIs
                </p>

                <p className="mt-2 break-words text-sm font-semibold text-slate-900">
                  {Array.isArray(device.related_imsis) &&
                  device.related_imsis.length > 0
                    ? device.related_imsis.join(", ")
                    : "Not available"}
                </p>
              </div>
            </div>
          </article>
        );
      })}
    </section>
  );
}
