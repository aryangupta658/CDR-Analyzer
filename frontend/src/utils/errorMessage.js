export function getErrorMessage(
  error,
  fallback = "Something went wrong.",
) {
  const detail =
    error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(
          item.loc,
        )
          ? item.loc
              .filter(
                (part) =>
                  part !== "body",
              )
              .join(".")
          : "";

        if (field) {
          return `${field}: ${item.msg}`;
        }

        return item.msg;
      })
      .filter(Boolean)
      .join(", ");
  }

  return (
    error?.message ||
    fallback
  );
}