import Link from "next/link";

/** Compact wordmark for headers — logo breathes, no boxed image. */
export function Wordmark({
  href = "/",
  tone = "dark",
  size = "md",
}: {
  href?: string;
  tone?: "dark" | "light";
  size?: "sm" | "md";
}) {
  const color = tone === "dark" ? "text-[#c8d9d0]" : "text-accent";
  const scale = size === "sm" ? "text-xl" : "text-2xl";
  return (
    <Link href={href} className={`font-display font-semibold tracking-[0.12em] ${scale} ${color}`}>
      i<span className="brand-orb" aria-hidden />PÌLẸ̀
    </Link>
  );
}
