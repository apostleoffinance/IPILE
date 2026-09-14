import Image from "next/image";

export function BrandMark({
  variant = "light",
  showTagline = false,
  size = "md",
}: {
  variant?: "light" | "dark";
  showTagline?: boolean;
  size?: "sm" | "md" | "lg";
}) {
  const text = variant === "dark" ? "text-[#9fb8ad]" : "text-accent";
  const title =
    size === "lg" ? "text-5xl md:text-6xl" : size === "sm" ? "text-2xl" : "text-3xl";

  return (
    <div className={variant === "dark" ? "text-center" : ""}>
      {variant === "dark" ? (
        <Image
          src="/brand/ipile-logo.jpg"
          alt="IPÌLẸ̀ — The financial foundation for households everywhere"
          width={720}
          height={400}
          className="mx-auto h-auto w-full max-w-md"
          priority
        />
      ) : (
        <>
          <p className={`font-display font-semibold tracking-[0.08em] ${title} ${text}`}>
            i<span className="brand-orb" aria-hidden />PÌLẸ̀
          </p>
          {showTagline ? (
            <>
              <div className="gold-rule mx-auto mt-3 w-40" />
              <p className="mt-3 text-[11px] uppercase tracking-[0.22em] text-muted">
                The financial foundation for households everywhere
              </p>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
