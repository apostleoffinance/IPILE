type ConfirmationDialogProps = {
  title: string;
  body: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onClose: () => void;
};

export function ConfirmationDialog({
  title,
  body,
  confirmLabel = "Confirm",
  onConfirm,
  onClose,
}: ConfirmationDialogProps) {
  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-md border border-line bg-surface p-6">
        <h2 className="text-lg font-medium">{title}</h2>
        <p className="mt-2 text-sm text-muted">{body}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" className="text-sm text-muted" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="rounded-md bg-accent px-3 py-2 text-sm text-white" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
