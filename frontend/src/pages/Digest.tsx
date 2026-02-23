import React, { useState } from 'react';
import { BookOpen, RefreshCw, Sparkles } from 'lucide-react';
import { useRelationship } from '../contexts/RelationshipContext';
import { useDigests } from '../hooks/useDigests';
import DigestCard from '../components/digest/DigestCard';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const Digest: React.FC = () => {
  const { relationshipId } = useRelationship();
  const rid = relationshipId || '00000000-0000-0000-0000-000000000000';
  const { digests, loading, error, refetch } = useDigests(rid);
  const [generating, setGenerating] = useState(false);
  const [selectedDigest, setSelectedDigest] = useState<string | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/digests/generate?relationship_id=${rid}`,
        {
          method: 'POST',
          headers: { 'ngrok-skip-browser-warning': 'true' },
        }
      );
      if (res.ok) {
        refetch();
      }
    } catch (e) {
      console.error('Error generating digest:', e);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <BookOpen size={24} className="text-accent" />
          <h1 className="text-h1 text-text-primary">Weekly Digests</h1>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent/10 text-accent hover:bg-accent/20 transition-colors text-small font-medium disabled:opacity-50"
        >
          {generating ? (
            <RefreshCw size={16} className="animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}
          {generating ? 'Generating...' : 'Generate Now'}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-surface-elevated rounded-2xl p-6 border border-border-subtle animate-pulse">
              <div className="h-4 bg-surface-hover rounded w-1/3 mb-4" />
              <div className="h-3 bg-surface-hover rounded w-full mb-2" />
              <div className="h-3 bg-surface-hover rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12 text-text-secondary">
          <p>Error loading digests: {error}</p>
        </div>
      ) : digests.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen size={48} className="text-text-tertiary mx-auto mb-4" />
          <h3 className="text-h3 text-text-primary mb-2">No digests yet</h3>
          <p className="text-small text-text-secondary mb-6">
            Weekly digests summarize your relationship patterns and growth.
            Click "Generate Now" to create your first one.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {digests.map((digest) => (
            <DigestCard
              key={digest.id}
              digest={digest}
              onClick={() => setSelectedDigest(selectedDigest === digest.id ? null : digest.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default Digest;
