import { downloadBatchReport, printBatchReport } from '../printBatchReport';

describe('printBatchReport', () => {
  const originalPrint = window.print;

  afterEach(() => {
    window.print = originalPrint;
  });

  it('calls window.print when available', () => {
    window.print = jest.fn();

    printBatchReport();

    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it('throws when print is unavailable', () => {
    window.print = undefined;

    expect(() => printBatchReport()).toThrow('Browser print is not available');
  });

  it('exposes downloadBatchReport as an alias', () => {
    expect(downloadBatchReport).toBe(printBatchReport);
  });
});
