import { Phone, Users } from "lucide-react";

import {
  getContactArray,
  formatVisualizationDuration,
} from "../../utils/visualizationHelpers";

function calculatePosition(index, total, radius, centreX, centreY) {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2;

  return {
    x: centreX + radius * Math.cos(angle),

    y: centreY + radius * Math.sin(angle),
  };
}

export default function ContactNetworkGraph({ phoneNumber, contacts }) {
  const contactList = getContactArray(contacts).slice(0, 12);

  if (!phoneNumber) {
    return null;
  }

  if (contactList.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Users size={34} className="mx-auto text-slate-300" />

        <h3 className="mt-4 font-bold text-slate-900">
          No contact network available
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          Analyse a number with contact activity to display its network.
        </p>
      </section>
    );
  }

  const width = 900;
  const height = 540;

  const centreX = width / 2;
  const centreY = height / 2;

  const radius = contactList.length <= 6 ? 185 : 210;

  const maximumRecords = Math.max(
    ...contactList.map((item) =>
      Number(item.total_records || item.record_count || 1),
    ),
    1,
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-lg font-bold text-slate-950">Contact network</h2>

        <p className="mt-1 text-sm text-slate-500">
          Line thickness represents the relative number of communication
          records.
        </p>
      </div>

      <div className="mt-5 overflow-x-auto rounded-xl bg-slate-50">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="min-h-[440px] min-w-[720px] w-full"
          role="img"
          aria-label={`Contact network for ${phoneNumber}`}
        >
          {contactList.map((contact, index) => {
            const position = calculatePosition(
              index,
              contactList.length,
              radius,
              centreX,
              centreY,
            );

            const records = Number(
              contact.total_records || contact.record_count || 1,
            );

            const lineWidth = 1.5 + (records / maximumRecords) * 7;

            return (
              <line
                key={`line-${contact.contact_number}-${index}`}
                x1={centreX}
                y1={centreY}
                x2={position.x}
                y2={position.y}
                stroke="#93c5fd"
                strokeWidth={lineWidth}
                strokeLinecap="round"
              />
            );
          })}

          <circle cx={centreX} cy={centreY} r="65" fill="#2563eb" />

          <text
            x={centreX}
            y={centreY - 7}
            textAnchor="middle"
            fill="white"
            fontSize="15"
            fontWeight="700"
          >
            Selected number
          </text>

          <text
            x={centreX}
            y={centreY + 18}
            textAnchor="middle"
            fill="white"
            fontSize="14"
          >
            {phoneNumber}
          </text>

          {contactList.map((contact, index) => {
            const position = calculatePosition(
              index,
              contactList.length,
              radius,
              centreX,
              centreY,
            );

            const records = Number(
              contact.total_records || contact.record_count || 0,
            );

            return (
              <g key={`${contact.contact_number}-${index}`}>
                <circle
                  cx={position.x}
                  cy={position.y}
                  r="53"
                  fill="#ffffff"
                  stroke="#bfdbfe"
                  strokeWidth="3"
                />

                <text
                  x={position.x}
                  y={position.y - 12}
                  textAnchor="middle"
                  fill="#0f172a"
                  fontSize="13"
                  fontWeight="700"
                >
                  {contact.contact_number}
                </text>

                <text
                  x={position.x}
                  y={position.y + 10}
                  textAnchor="middle"
                  fill="#475569"
                  fontSize="12"
                >
                  {records} records
                </text>

                <text
                  x={position.x}
                  y={position.y + 28}
                  textAnchor="middle"
                  fill="#64748b"
                  fontSize="10"
                >
                  {formatVisualizationDuration(contact.total_duration_seconds)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-xs">
        <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 font-semibold text-blue-700">
          <Phone size={14} />
          Centre: analysed number
        </span>

        <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 font-semibold text-slate-600">
          <Users size={14} />
          Outer nodes: contacts
        </span>
      </div>
    </section>
  );
}
