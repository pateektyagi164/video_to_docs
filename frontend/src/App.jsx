import { useState } from 'react';
import Header from './components/layout/Header';
import UploadZone from './components/features/UploadZone';
import ProgressBar from './components/features/ProgressBar';
import DocumentViewer from './components/features/DocumentViewer';

export default function App() {
  const [appState, setAppState] = useState('IDLE'); 
  const [jobId, setJobId] = useState(null);
  const [documentContent, setDocumentContent] = useState('');

  const handleJobStarted = (id) => {
    setJobId(id);
    setAppState('PROCESSING');
  };

  const handleJobComplete = (markdown) => {
    setDocumentContent(markdown);
    setAppState('COMPLETE');
  };

  const resetApp = () => {
    setJobId(null);
    setDocumentContent('');
    setAppState('IDLE');
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 flex flex-col items-center">
      <Header />
      <main className="w-full max-w-4xl flex flex-col items-center justify-center flex-grow">
        {appState === 'IDLE' && <UploadZone onJobStarted={handleJobStarted} />}
        {appState === 'PROCESSING' && <ProgressBar jobId={jobId} onComplete={handleJobComplete} onReset={resetApp} />}
        {appState === 'COMPLETE' && <DocumentViewer markdown={documentContent} onReset={resetApp} />}
      </main>
    </div>
  );
}