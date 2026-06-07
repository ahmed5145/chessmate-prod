/**
 * Save the on-screen batch report via the browser print dialog.
 *
 * Users should pick "Save as PDF" (or similar) as the destination.
 * Browsers cannot silently write a PDF file without this dialog — that is a
 * platform security restriction, not something we can bypass in the web app.
 */

export const printBatchReport = () => {
  if (typeof window === 'undefined' || typeof window.print !== 'function') {
    throw new Error('Browser print is not available');
  }
  window.print();
};

/** @alias printBatchReport — primary owner-facing "download" path */
export const downloadBatchReport = printBatchReport;
