import { X } from "lucide-react";

export default function Modal({
  open,
  title,
  children,
  onClose,
  maxWidth = "max-w-3xl",
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
      <div
        className={`
          max-h-[90vh] w-full overflow-y-auto
          rounded-2xl border border-slate-200
          bg-white shadow-2xl
          ${maxWidth}
        `}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
