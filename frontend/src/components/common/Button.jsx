export default function Button({
  children,
  type = "button",
  variant = "primary",
  loading = false,
  disabled = false,
  className = "",
  ...props
}) {
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 shadow-sm",

    secondary:
      "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",

    orange: "bg-orange-500 text-white hover:bg-orange-600",

    danger: "bg-red-600 text-white hover:bg-red-700",
  };

  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`
        inline-flex min-h-11 items-center
        justify-center gap-2 rounded-xl
        px-5 py-2.5 text-sm font-semibold
        transition
        disabled:cursor-not-allowed
        disabled:opacity-60
        ${variants[variant]}
        ${className}
      `}
      {...props}
    >
      {loading ? "Please wait..." : children}
    </button>
  );
}
