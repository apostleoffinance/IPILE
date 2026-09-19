import Image from "next/image";
import Link from "next/link";

const LOGO_SRC = "/brand/Ipile1.png";
const LOGO_ALT = "IPÌLẸ̀";

const sizeClass = {
  sm: "h-8 w-auto",
  md: "h-12 w-auto",
  lg: "h-16 w-auto md:h-20",
} as const;

/** Brand logo image. Uses Ipile1.png as-is (no CSS wordmark). */
export function Wordmark({
  href = "/",
  size = "md",
  priority = false,
}: {
  href?: string;
  /** Kept for call-site compatibility; logo asset is unchanged. */
  tone?: "dark" | "light";
  size?: "sm" | "md" | "lg";
  priority?: boolean;
}) {
  return (
    <Link href={href} className="inline-flex shrink-0 items-center" aria-label={LOGO_ALT}>
      <Image
        src={LOGO_SRC}
        alt={LOGO_ALT}
        width={720}
        height={200}
        className={`${sizeClass[size]} object-contain object-left`}
        priority={priority}
      />
    </Link>
  );
}
