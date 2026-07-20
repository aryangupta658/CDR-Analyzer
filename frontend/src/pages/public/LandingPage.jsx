import {
  Clock3,
  MapPinned,
  Network,
  PhoneCall,
  Smartphone,
} from "lucide-react";

import { Link } from "react-router";

const features = [
  {
    title: "Number Analysis",
    description:
      "Review contacts, call direction, frequency and communication history.",
    icon: PhoneCall,
    color: "bg-blue-50 text-blue-600",
  },
  {
    title: "Device Analysis",
    description:
      "Examine IMEI, IMSI, device history and shared-device associations.",
    icon: Smartphone,
    color: "bg-violet-50 text-violet-600",
  },
  {
    title: "Location Analysis",
    description:
      "Review cell towers, location history, movement and co-location results.",
    icon: MapPinned,
    color: "bg-emerald-50 text-emerald-600",
  },
  {
    title: "Incident Analysis",
    description:
      "Study communication and tower activity around a selected incident time.",
    icon: Clock3,
    color: "bg-orange-50 text-orange-600",
  },
];

export default function LandingPage() {
  return (
    <>
      <section className="overflow-hidden bg-gradient-to-br from-white via-blue-50/30 to-orange-50/30">
        <div className="mx-auto grid min-h-[650px] max-w-7xl items-center gap-10 px-4 py-14 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white px-4 py-2 text-sm font-medium text-blue-700">
              <Network size={16} />
              Call Detail Record Analysis
            </span>

            <h1 className="mt-6 max-w-xl text-4xl font-bold leading-tight text-slate-950 sm:text-5xl lg:text-6xl">
              CDR analysis
              <span className="text-blue-600"> made easier</span>
            </h1>

            <p className="mt-6 max-w-xl text-base leading-8 text-slate-600 sm:text-lg">
              Import call detail records and examine numbers, devices, towers
              and incident timelines through one case-based workspace.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/signup"
                className="rounded-xl bg-blue-600 px-6 py-3 text-center font-semibold text-white shadow-sm hover:bg-blue-700"
              >
                Get Started
              </Link>

              <a
                href="#features"
                className="rounded-xl border border-slate-300 bg-white px-6 py-3 text-center font-semibold text-slate-700 hover:bg-slate-50"
              >
                View Features
              </a>
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-10 rounded-full bg-blue-200/40 blur-3xl" />

            <img
              src="/images/cdr-hero.png"
              alt="Telecom tower and CDR analysis symbols"
              className="relative mx-auto w-full max-w-2xl object-contain"
            />
          </div>
        </div>
      </section>

      <section id="features" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold text-slate-950">
              Analysis modules
            </h2>

            <p className="mt-3 text-slate-500">
              Select an imported evidence file and work with the analysis needed
              for the investigation.
            </p>
          </div>

          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <article
                  key={feature.title}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
                >
                  <span
                    className={`
                      flex h-12 w-12
                      items-center justify-center
                      rounded-xl
                      ${feature.color}
                    `}
                  >
                    <Icon size={23} />
                  </span>

                  <h3 className="mt-5 font-bold text-slate-950">
                    {feature.title}
                  </h3>

                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    {feature.description}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="border-t border-slate-200 bg-slate-50 py-20"
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-3xl font-bold text-slate-950">
            How it works
          </h2>

          <div className="mt-12 grid gap-6 md:grid-cols-4">
            {[
              "Create or open a case",
              "Upload a CDR file",
              "Map and import records",
              "Run evidence-level analysis",
            ].map((text, index) => (
              <div
                key={text}
                className="rounded-2xl bg-white p-6 text-center shadow-sm"
              >
                <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-bold text-white">
                  {index + 1}
                </span>

                <p className="mt-4 font-semibold text-slate-800">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
