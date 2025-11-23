import React from 'react';
import { useNavigate } from 'react-router-dom';
import { HeartIcon, MicIcon, BarChartIcon, FileTextIcon, Clock } from 'lucide-react';
const Home = () => {
  const navigate = useNavigate();
  return <div className="flex flex-col items-center justify-center min-h-[80vh] text-center">
      <div className="mb-2 p-4 rounded-full bg-white/30 backdrop-blur-sm">
        <HeartIcon size={40} className="text-rose-400" />
      </div>
      <h1 className="text-3xl font-bold text-gray-800 mb-1">HeartSync</h1>
      <p className="text-lg text-gray-600 mb-10">
        Your voice-guided relationship mediator.
      </p>
      <div className="space-y-3 w-full max-w-xs">
        <button onClick={() => navigate('/fight-capture')} className="w-full py-3 px-4 bg-white/70 hover:bg-white/90 rounded-xl flex items-center justify-center transition-all shadow-soft hover:shadow-cozy">
          <MicIcon size={18} className="mr-2 text-rose-500" />
          <span className="font-medium">Start Fight Capture</span>
        </button>
        <button onClick={() => navigate('/post-fight')} className="w-full py-3 px-4 bg-white/70 hover:bg-white/90 rounded-xl flex items-center justify-center transition-all shadow-soft hover:shadow-cozy">
          <HeartIcon size={18} className="mr-2 text-rose-500" />
          <span className="font-medium">Enter Post-Fight Session</span>
        </button>
        <button onClick={() => navigate('/analytics')} className="w-full py-3 px-4 bg-white/70 hover:bg-white/90 rounded-xl flex items-center justify-center transition-all shadow-soft hover:shadow-cozy">
          <BarChartIcon size={18} className="mr-2 text-rose-500" />
          <span className="font-medium">View Analytics</span>
        </button>
        <button onClick={() => navigate('/upload')} className="w-full py-3 px-4 bg-white/70 hover:bg-white/90 rounded-xl flex items-center justify-center transition-all shadow-soft hover:shadow-cozy">
          <FileTextIcon size={18} className="mr-2 text-rose-500" />
          <span className="font-medium">Upload PDFs & Data</span>
        </button>
        <button onClick={() => navigate('/history')} className="w-full py-3 px-4 bg-white/70 hover:bg-white/90 rounded-xl flex items-center justify-center transition-all shadow-soft hover:shadow-cozy">
          <Clock size={18} className="mr-2 text-rose-500" />
          <span className="font-medium">History</span>
        </button>
      </div>
    </div>;
};
export default Home;