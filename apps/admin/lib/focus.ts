export function focusFirstDialogControl(event: Event) {
  const dialog = event.currentTarget;
  if (!(dialog instanceof HTMLElement)) return;

  const firstField = dialog.querySelector<HTMLElement>(
    "input:not([type='hidden']):not([disabled]), select:not([disabled]), textarea:not([disabled])",
  );
  const firstControl = firstField ?? dialog.querySelector<HTMLElement>("button:not([disabled])");
  if (!firstControl) return;

  event.preventDefault();
  firstControl.focus();
}
