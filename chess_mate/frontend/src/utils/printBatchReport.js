/** Open the browser print dialog for the on-screen batch report. */

export const printBatchReport = () => {
  if (typeof window === 'undefined' || typeof window.print !== 'function') {
    throw new Error('Browser print is not available');
  }
  window.print();
};
