/**
 * Client-side PDF download for batch coach reports.
 * Captures an off-screen clone so the live page never flashes light mode.
 */

const PDF_EXPORT_CLASS = 'batch-report-pdf-export';
const PDF_HOST_ID = 'chessmate-pdf-capture-host';

const expandReportAccordions = (root) => {
  root.querySelectorAll('.MuiAccordion-root').forEach((accordion) => {
    accordion.classList.add('Mui-expanded');
    const summary = accordion.querySelector('.MuiAccordionSummary-root');
    const details = accordion.querySelector('.MuiAccordionDetails-root');
    const collapse = accordion.querySelector('.MuiCollapse-root');
    if (summary) {
      summary.setAttribute('aria-expanded', 'true');
    }
    if (details) {
      details.style.display = 'block';
      details.style.height = 'auto';
      details.style.visibility = 'visible';
    }
    if (collapse) {
      collapse.style.height = 'auto';
      collapse.style.visibility = 'visible';
      collapse.classList.remove('MuiCollapse-hidden');
    }
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

const removePdfHost = () => {
  const existing = document.getElementById(PDF_HOST_ID);
  if (existing) {
    existing.remove();
  }
};

const buildCaptureClone = (root) => {
  removePdfHost();

  const host = document.createElement('div');
  host.id = PDF_HOST_ID;
  host.setAttribute('aria-hidden', 'true');
  host.style.cssText = [
    'position:fixed',
    'left:-20000px',
    'top:0',
    `width:${Math.max(root.scrollWidth, root.offsetWidth)}px`,
    'overflow:visible',
    'pointer-events:none',
    'z-index:-1',
  ].join(';');

  const clone = root.cloneNode(true);
  clone.classList.add(PDF_EXPORT_CLASS);
  expandReportAccordions(clone);
  host.appendChild(clone);
  document.body.appendChild(host);

  return { host, clone };
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

  const { host, clone } = buildCaptureClone(root);

  await new Promise((resolve) => {
    window.setTimeout(resolve, 400);
  });

  try {
    const canvas = await html2canvas(clone, {
      scale: 1.5,
      useCORS: true,
      allowTaint: false,
      logging: false,
      backgroundColor: '#ffffff',
      scrollX: 0,
      scrollY: 0,
      width: clone.scrollWidth,
      height: clone.scrollHeight,
      windowWidth: clone.scrollWidth,
      windowHeight: clone.scrollHeight,
      onclone: (doc) => {
        const clonedRoot = doc.querySelector(`.${PDF_EXPORT_CLASS}`);
        if (clonedRoot) {
          clonedRoot.classList.add(PDF_EXPORT_CLASS);
        }
        doc.documentElement.style.background = '#ffffff';
        doc.body.style.background = '#ffffff';
      },
    });

    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    sliceCanvasToPdf(canvas, pdf, 10, pageWidth, pageHeight);
    pdf.save(filename);
  } finally {
    removePdfHost();
  }
};
