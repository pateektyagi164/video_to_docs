import { useState } from 'react';
import { UploadCloud, FileVideo } from 'lucide-react';
import { apiClient } from '../../api/client';

// ... (keep your imports)

export default function UploadZone({ onJobStarted }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      // UPGRADED: Pass the actual 'file' object, not 'file.name'
      const data = await apiClient.startExtraction(file);
      
      if (data && data.job_id) {
        onJobStarted(data.job_id);
      } else {
        throw new Error("No Job ID returned from server.");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to connect to backend.");
      setLoading(false);
    }
  };

// ... (keep the rest of your JSX exactly the same)
  return (
    <div className="w-full max-w-xl animate-in fade-in zoom-in duration-500">
      <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-gray-800 border-dashed rounded-xl cursor-pointer bg-gray-900/50 hover:bg-gray-900/80 hover:border-emerald-500/50 transition-all duration-200">
        <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
          {loading ? (
            <div className="animate-pulse flex flex-col items-center">
              <FileVideo className="w-12 h-12 text-emerald-500 mb-3" />
              <p className="text-lg text-gray-300">Dispatching to Worker...</p>
            </div>
          ) : (
            <>
              <UploadCloud className="w-12 h-12 text-gray-500 mb-3" />
              <p className="mb-2 text-lg font-medium text-gray-300">Click to upload video</p>
              <p className="text-sm text-gray-500">Simulating File Pipeline (Local Path)</p>
            </>
          )}
        </div>
        <input type="file" className="hidden" accept="video/*" onChange={handleFileSelect} disabled={loading} />
      </label>
      {error && <div className="mt-4 p-4 bg-red-900/20 border border-red-900 rounded-lg text-red-400 text-sm text-center">{error}</div>}
    </div>
  );
}