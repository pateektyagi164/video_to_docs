import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = {
  // UPGRADED: Accepts the raw File object and transmits it securely
  startExtraction: async (fileObj) => {
    const formData = new FormData();
    // 'video_file' must match the parameter name in your FastAPI route
    formData.append('video_file', fileObj); 

    const response = await axios.post(`${BASE_URL}/extract`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data' // Tells FastAPI a physical file is coming
      }
    });
    return response.data;
  },

  getProgressUrl: (jobId) => {
    return `${BASE_URL}/progress/${jobId}`;
  }
};
