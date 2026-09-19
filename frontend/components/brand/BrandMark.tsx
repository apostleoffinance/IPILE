import Image from "next/image";

const LOGO_SRC = "/brand/Ipile1.png";
const LOGO_ALT = "IPÌLẸ̀. The financial foundation for households everywhere";

const sizeClass = {
  sm: "h-10 w-auto max-w-[160px]",
  md: "h-14 w-auto max-w-[240px]",
  lg: "h-auto w-full max-w-md",
} as const;

/** Full brand mark using Ipile1.png as-is. */
export function BrandMark({
  size = "md",
  priority = false,
}: {
  /** Kept for call-site compatibility. */
  variant?: "light" | "dark";
  showTagline?: boolean;
  size?: "sm" | "md" | "lg";
  priority?: boolean;
}) {
  return (
    <div className="inline-flex">
      <Image
        src={LOGO_SRC}
        alt={LOGO_ALT}
        width={720}
        height={200}
        className={`${sizeClass[size]} object-contain`}
        priority={priority || size === "lg"}
      />
    </div>
  );
}
