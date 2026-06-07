/**
 * Client-side PDF download for batch coach reports.
 */

const PDF_EXPORT_CLASS = 'batch-report-pdf-export';

const expandReportAccordions = (root) => {
  const summaries = root.querySelectorAll('.MuiAccordionSummary-root[aria-expanded="false"]');
  summaries.forEach((summary) => {
    summary.click();
  });
};

const sliceCanvasToPdf = (canvas, pdf, margin, pageWidth, pageHeight) => {
  const printableWidth = pageWidth - margin * 2;
  const printableHeight = pageHeight - margin * 2;
  const scale = printableWidth / canvas.width;
  const pageSliceHeight = Math.floor(printableHeight / scale);

  let offsetY = 0;
  let pageIndex = 0;

  while (offsetY < canvas.height) {
    const sliceHeight = Math.min(pageSliceHeight, canvas.height - offsetY);
    const pageCanvas = document.createElement('canvas');
    pageCanvas.width = canvas.width;
    pageCanvas.height = sliceHeight;

    const ctx = pageCanvas.getContext('2d');
    if (!ctx) {
      throw new Error('Could not prepare PDF page');
    }

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
    ctx.drawImage(
      canvas,
      0,
      offsetY,
      canvas.width,
      sliceHeight,
      0,
      0,
      canvas.width,
      sliceHeight
    );

    const imageData = pageCanvas.toDataURL('image/png');
    const imageHeightMm = sliceHeight * scale;

    if (pageIndex > 0) {
      pdf.addPage();
    }

    pdf.addImage(imageData, 'PNG', margin, margin, printableWidth, imageHeightMm);
    offsetY += sliceHeight;
    pageIndex += 1;
  }
};

export const downloadReportPdf = async (filename = 'chessmate-batch-report.pdf') => {
  const root = document.querySelector('.batch-report-print-root');
  if (!root) {
    throw new Error('Report content not found');
  }

  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
    import('html2canvas'),
    import('jspdf'),
  ]);

  root.classList.add(PDF_EXPORT_CLASS);
  expandReportAccordions(root);
  window.scrollTo(0, 0);

  await new Promise((resolve) => {
    window.setTimeout(resolve, 450);
  });

  try {
    const canvas = await html2canvas(root, {
      scale: 1.5,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
      scrollX: 0,
      scrollY: -window.scrollY,
      windowWidth: root.scrollWidth,
      ignoreElements: (element) => element.classList?.contains('batch-report-no-print'),
      onclone: (doc) => {
        const clonedRoot = doc.querySelector('.batch-report-print-root');
        if (clonedRoot) {
          clonedRoot.classList.add(PDF_EXPORT_CLASS);
        }
      },
    });

    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    sliceCanvasToPdf(canvas, pdf, 10, pageWidth, pageHeight);
    pdf.save(filename);
  } finally {
    root.classList.remove(PDF_EXPORT_CLASS);
  }
};
