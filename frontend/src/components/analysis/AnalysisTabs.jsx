export default function AnalysisTabs({ tabs, activeTab, onChange }) {
  return (
    <div className="overflow-x-auto">
      <div className="inline-flex min-w-full gap-1 rounded-xl bg-slate-100 p-1 sm:min-w-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;

          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              className={`
                inline-flex min-h-11
                flex-1 items-center
                justify-center gap-2
                whitespace-nowrap
                rounded-lg px-4
                text-sm font-semibold
                transition
                ${
                  isActive
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-slate-500 hover:bg-white/60 hover:text-slate-800"
                }
              `}
            >
              {Icon && <Icon size={17} />}

              {tab.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
