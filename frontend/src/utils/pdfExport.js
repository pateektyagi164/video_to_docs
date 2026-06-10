import html2pdf from 'html2pdf.js';

export const downloadAsPDF = (elementId, filename = 'AI_Knowledge_Extraction.pdf') => {
  const element = document.getElementById(elementId);
  if (!element) return;

  const opt = {
    margin:       [0.5, 0.5, 0.5, 0.5],
    filename:     filename,
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true, logging: false },
    jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
  };

  html2pdf().set(opt).from(element).save();
};