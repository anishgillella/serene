import React from 'react';
import { SearchIcon, ZapIcon } from 'lucide-react';
import type { MossContextEvent } from '../../hooks/useMossContextEvents';

interface MossResultsPanelProps {
  latest: MossContextEvent | null;
  events: MossContextEvent[];
}

const MossResultsPanel: React.FC<MossResultsPanelProps> = ({ latest, events }) => {
  if (!latest && events.length === 0) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        <SearchIcon size={20} className="mx-auto mb-2 opacity-40" />
        <p>Luna's retrieval matches will appear here</p>
      </div>
    );
  }

  const display = latest || events[0];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-3 py-2 border-b border-white/10 flex items-center gap-2">
        <ZapIcon size={14} className="text-accent" />
        <span className="text-xs font-medium text-gray-300">Moss Retrieval</span>
        {display.time_taken_ms != null && (
          <span className="text-xs text-gray-500 ml-auto">{display.time_taken_ms.toFixed(1)}ms</span>
        )}
      </div>

      <div className="px-3 py-2 border-b border-white/5">
        <p className="text-xs text-gray-500 mb-1">Query</p>
        <p className="text-sm text-gray-200">{display.query}</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {display.matches.length === 0 ? (
          <p className="text-xs text-gray-500">No matches found</p>
        ) : (
          display.matches.map((match, i) => (
            <div
              key={i}
              className="p-2 rounded-lg bg-white/5 border border-white/10 text-xs"
            >
              {match.score != null && (
                <span className="text-accent/80 font-mono text-[10px]">
                  {(match.score * 100).toFixed(0)}% match
                </span>
              )}
              <p className="text-gray-300 mt-1 line-clamp-4">{match.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MossResultsPanel;
