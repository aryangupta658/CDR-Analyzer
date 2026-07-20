function formatLabel(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "number") {
    return new Intl.NumberFormat("en-IN").format(value);
  }

  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    const date = new Date(value);

    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleString("en-IN");
    }
  }

  return String(value);
}

function PrimitiveCard({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {formatLabel(label)}
      </p>

      <p className="mt-2 break-words text-sm font-semibold text-slate-900">
        {formatValue(value)}
      </p>
    </div>
  );
}

function ObjectSection({ title, data, level }) {
  const primitiveEntries = Object.entries(data).filter(
    ([, value]) => value === null || typeof value !== "object",
  );

  const complexEntries = Object.entries(data).filter(
    ([, value]) => value !== null && typeof value === "object",
  );

  return (
    <section
      className={`
        rounded-2xl border
        border-slate-200 bg-white
        ${level === 0 ? "p-5 shadow-sm sm:p-6" : "p-4"}
      `}
    >
      {title && (
        <h2
          className={`
            font-bold text-slate-950
            ${level === 0 ? "text-xl" : "text-base"}
          `}
        >
          {formatLabel(title)}
        </h2>
      )}

      {primitiveEntries.length > 0 && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {primitiveEntries.map(([key, value]) => (
            <PrimitiveCard key={key} label={key} value={value} />
          ))}
        </div>
      )}

      {complexEntries.length > 0 && (
        <div className="mt-5 space-y-5">
          {complexEntries.map(([key, value]) => (
            <RenderValue
              key={key}
              title={key}
              value={value}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ArrayTable({ title, items }) {
  if (items.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="font-bold text-slate-950">{formatLabel(title)}</h3>

        <p className="mt-3 text-sm text-slate-500">No results were found.</p>
      </section>
    );
  }

  const allObjects = items.every(
    (item) => item && typeof item === "object" && !Array.isArray(item),
  );

  if (!allObjects) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="font-bold text-slate-950">{formatLabel(title)}</h3>

        <div className="mt-4 flex flex-wrap gap-2">
          {items.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className="rounded-full bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700"
            >
              {formatValue(item)}
            </span>
          ))}
        </div>
      </section>
    );
  }

  const columns = Array.from(
    new Set(
      items.flatMap((item) =>
        Object.keys(item).filter(
          (key) => item[key] === null || typeof item[key] !== "object",
        ),
      ),
    ),
  );

  const nestedColumns = Array.from(
    new Set(
      items.flatMap((item) =>
        Object.keys(item).filter(
          (key) => item[key] !== null && typeof item[key] === "object",
        ),
      ),
    ),
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-slate-950">{formatLabel(title)}</h3>

        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
          {items.length} result
          {items.length !== 1 ? "s" : ""}
        </span>
      </div>

      {columns.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    className="whitespace-nowrap border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500"
                  >
                    {formatLabel(column)}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {items.map((item, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-slate-50">
                  {columns.map((column) => (
                    <td
                      key={column}
                      className="whitespace-nowrap border-b border-slate-100 px-4 py-3 text-slate-700"
                    >
                      {formatValue(item[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {nestedColumns.length > 0 && (
        <div className="mt-5 space-y-4">
          {items.map((item, index) => (
            <div
              key={index}
              className="rounded-xl border border-slate-200 bg-slate-50 p-4"
            >
              <p className="mb-3 text-sm font-bold text-slate-800">
                Result {index + 1}
              </p>

              <div className="space-y-4">
                {nestedColumns.map((column) => (
                  <RenderValue
                    key={column}
                    title={column}
                    value={item[column]}
                    level={2}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function RenderValue({ title, value, level = 0 }) {
  if (Array.isArray(value)) {
    return <ArrayTable title={title} items={value} />;
  }

  if (value && typeof value === "object") {
    return <ObjectSection title={title} data={value} level={level} />;
  }

  return <PrimitiveCard label={title} value={value} />;
}

export default function AnalysisResult({ data, title = "Analysis Result" }) {
  if (!data) {
    return null;
  }

  return (
    <div className="mt-7 space-y-5">
      <div>
        <h2 className="text-xl font-bold text-slate-950">{title}</h2>

        <p className="mt-1 text-sm text-slate-500">
          The information below was produced from the selected case and
          evidence.
        </p>
      </div>

      <RenderValue title={title} value={data} level={0} />
    </div>
  );
}
