import React, { useEffect, useState } from 'react';
import { GitCommit, GitMerge, AlertCircle, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface RelatedConflict {
    id: string;
    summary: string;
    type: 'saga' | 'topic';
    reason: string;
}

interface RelatedConflictsProps {
    conflictId: string;
    apiBase: string;
}

export function RelatedConflicts({ conflictId, apiBase }: RelatedConflictsProps) {
    const [related, setRelated] = useState<RelatedConflict[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchRelated = async () => {
            try {
                const res = await fetch(`${apiBase}/api/post-fight/conflicts/${conflictId}/related`, {
                    headers: {
                        'ngrok-skip-browser-warning': 'true'
                    }
                });
                if (res.ok) {
                    const data = await res.json();
                    setRelated(data.related_conflicts || []);
                }
            } catch (error) {
                console.error("Failed to fetch related conflicts:", error);
            } finally {
                setLoading(false);
            }
        };

        if (conflictId) {
            fetchRelated();
        }
    }, [conflictId, apiBase]);

    if (loading) return null;
    if (related.length === 0) return null;

    const sagas = related.filter(r => r.type === 'saga');
    const topics = related.filter(r => r.type === 'topic');

    return (
        <Card className="w-full bg-white/80 backdrop-blur-sm border-purple-100 shadow-sm mt-6">
            <CardHeader className="pb-2">
                <CardTitle className="text-lg font-medium flex items-center gap-2 text-purple-900">
                    <GitMerge className="h-5 w-5 text-purple-600" />
                    Conflict Patterns
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-6">
                    {/* Saga View (Timeline) */}
                    {sagas.length > 0 && (
                        <div>
                            <h4 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
                                <GitCommit className="h-4 w-4" />
                                This is a continuation of...
                            </h4>
                            <div className="space-y-3 pl-2 border-l-2 border-purple-200 ml-1">
                                {sagas.map((conflict) => (
                                    <div key={conflict.id} className="pl-4 relative">
                                        <div className="absolute -left-[21px] top-1.5 h-3 w-3 rounded-full bg-purple-400 border-2 border-white" />
                                        <p className="text-sm text-gray-600 font-medium">{conflict.reason}</p>
                                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{conflict.summary}</p>
                                    </div>
                                ))}
                                <div className="pl-4 relative">
                                    <div className="absolute -left-[21px] top-1.5 h-3 w-3 rounded-full bg-purple-600 border-2 border-white animate-pulse" />
                                    <p className="text-sm font-medium text-purple-900">Today's Conflict</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Topic View (Badges) */}
                    {topics.length > 0 && (
                        <div>
                            <h4 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
                                <AlertCircle className="h-4 w-4" />
                                Recurring Themes
                            </h4>
                            <div className="grid gap-3 sm:grid-cols-2">
                                {topics.map((conflict) => (
                                    <div key={conflict.id} className="bg-purple-50 p-3 rounded-lg border border-purple-100">
                                        <div className="flex items-start gap-2">
                                            <Calendar className="h-4 w-4 text-purple-400 mt-0.5" />
                                            <div>
                                                <p className="text-sm font-medium text-purple-900">{conflict.reason}</p>
                                                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{conflict.summary}</p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
