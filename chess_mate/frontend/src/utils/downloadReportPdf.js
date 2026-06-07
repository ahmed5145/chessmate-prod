/**
 * Client-side PDF download for batch coach reports.
 */

export const downloadReportPdf = async (filename = 'chessmate-batch-report.pdf') => {
  const root = document.querySelector('.batch-report-print-root');
  if (!root) {
    throw new Error('Report content not found');
  }

  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
    import('html2canvas'),
    import('jspdf'),
  ]);

  const canvas = await html2canvas(root, {
    scale: 2,
    useCORS: true,
    logging: false,
    backgroundColor: '#ffffff',
    ignoreElements: (element) => element.classList?.contains('batch-report-no-print'),
  });

  const imageData = canvas.toDataURL('image/png');
  const pdf = new jsPDF('p', 'mm', 'a4');
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 8;
  const printableWidth = pageWidth - margin * 2;
  const imageHeight = (canvas.height * printableWidth) / canvas.width;
  let heightLeft = imageHeight;
  let position = margin;

  pdf.addImage(imageData, 'PNG', margin, position, printableWidth, imageHeight);
  heightLeft -= pageHeight - margin * 2;

  while (heightLeft > 0) {
    position = margin - (imageHeight - heightLeft);
    pdf.addPage();
    pdf.addImage(imageData, 'PNG', margin, position, printableWidth, imageHeight);
    heightLeft -= pageHeight - margin * 2;
  }

  pdf.save(filename);
};
