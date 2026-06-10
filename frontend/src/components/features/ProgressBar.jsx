import { useState, useEffect, useRef } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { apiClient } from '../../api/client';

export default function ProgressBar({ jobId, onComplete, onReset }) {
  const [percent, setPercent] = useState(0);
  const [step, setStep] = useState('Initializing pipeline...');
  const [isError, setIsError] = useState(false);
  
  // Create a reference to hold our timeout timer
  const watchdogRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;

    const eventSource = new EventSource(apiClient.getProgressUrl(jobId));

    // The Watchdog Function
    const resetWatchdog = () => {
      if (watchdogRef.current) clearTimeout(watchdogRef.current);
      
      // If 90 seconds pass with NO updates, kill the connection and show an error
      watchdogRef.current = setTimeout(() => {
        setIsError(true);
        setStep("Error: Worker stalled or crashed silently. Connection timed out.");
        eventSource.close();
      }, 360000); 
    };

    // Start the timer as soon as we connect
    resetWatchdog();

    eventSource.onmessage = (event) => {
      try {
        // We received an update! The worker is alive. Reset the timer.
        resetWatchdog();

        const data = JSON.parse(event.data);
        setPercent(data.percent);
        setStep(data.step);

        if (data.percent === 100 && data.document) {
          clearTimeout(watchdogRef.current); // Stop the timer if successful
          eventSource.close();
          setTimeout(() => onComplete(data.document), 800); 
        }

        if (data.percent === -1) {
          clearTimeout(watchdogRef.current); // Stop the timer if it failed normally
          setIsError(true);
          setStep(`Error: ${data.error}`);
          eventSource.close();
        }
      } catch (err) {
        console.error("Failed to parse SSE data", err);
      }
    };

    eventSource.onerror = () => {
      clearTimeout(watchdogRef.current);
      setIsError(true);
      setStep("Lost connection to processing server.");
      eventSource.close();
    };

    // Cleanup when the component unmounts
    return () => {
      if (watchdogRef.current) clearTimeout(watchdogRef.current);
      eventSource.close();
    };
  }, [jobId, onComplete]);

  if (isError) {
    return (
      <div className="w-full max-w-xl p-6 bg-red-950/30 border border-red-900 rounded-xl text-center">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-red-400 mb-2">Processing Failed</h3>
        <p className="text-red-300/80 text-sm mb-6">{step}</p>
        <button onClick={onReset} className="px-4 py-2 bg-red-900 hover:bg-red-800 text-white rounded shadow transition-colors">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl p-8 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl animate-in fade-in duration-500">
      <div className="flex justify-between items-end mb-4">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 text-emerald-500 animate-spin" />
          <span className="text-gray-300 font-medium">{step}</span>
        </div>
        <span className="text-emerald-500 font-bold font-mono">{percent}%</span>
      </div>
      
      <div className="w-full h-3 bg-gray-950 rounded-full overflow-hidden border border-gray-800">
        <div 
          className="h-full bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)] transition-all duration-500 ease-out"
          style={{ width: `${Math.max(0, percent)}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 mt-4 text-center">Job ID: {jobId}</p>
    </div>
  );
}