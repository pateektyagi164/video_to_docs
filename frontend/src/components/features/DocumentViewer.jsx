import { useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useReactToPrint } from 'react-to-print';
import { FileDown, RefreshCw } from 'lucide-react';

export default function DocumentViewer({ markdown, onReset }) {
  // 1. Create the reference
  const contentRef = useRef(null);

  // 2. Use the updated v3 syntax: 'contentRef' instead of 'content'
  const handleDownloadPDF = useReactToPrint({
    contentRef: contentRef, 
    documentTitle: 'AI_Knowledge_Extraction',
  });

  const handleReset = () => {
      if (typeof onReset === 'function') {
          onReset();
      } else {
          window.location.reload();
      }
  };

  return (
    <div className="w-full max-w-5xl animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out pb-20">
      
      {/* Controls */}
      <div className="flex justify-end gap-4 mb-6">
        <button 
          onClick={handleReset}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg transition-colors border border-gray-700"
        >
          <RefreshCw className="w-4 h-4" /> Start Over
        </button>
        <button 
          onClick={() => handleDownloadPDF()}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all font-medium"
        >
          <FileDown className="w-4 h-4" /> Download PDF
        </button>
      </div>

      {/* The Styled Markdown Container */}
      {/* The ref MUST match the variable name exactly */}
      <div 
        ref={contentRef} 
        className="bg-white text-gray-900 p-10 md:p-16 rounded-xl shadow-2xl mx-auto border border-gray-800 print:shadow-none print:border-none"
      >
        <div className="prose prose-slate prose-lg max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {markdown}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}