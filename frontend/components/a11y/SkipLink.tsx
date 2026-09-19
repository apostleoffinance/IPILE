import Link from "next/link";

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="absolute left-4 top-0 z-[100] -translate-y-[120%] rounded-md bg-accent px-4 py-2 text-sm text-inverse transition focus:translate-y-4 focus:outline-none focus:ring-2 focus:ring-gold"
    >
      Skip to main content
    </a>
  );
}

