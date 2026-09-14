import type { Category } from "@/lib/api";

export function CategorySelector({
  categories,
  value,
  onChange,
}: {
  categories: Category[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <select
      className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">Uncategorized</option>
      {categories.map((category) => (
        <option key={category.id} value={category.id}>
          {category.name}
        </option>
      ))}
    </select>
  );
}
