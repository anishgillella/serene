import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Circle, ClipboardList } from 'lucide-react';

interface RepairComplianceProps {
  data: {
    has_data: boolean;
    conflict_id: string;
    steps: Array<{
      id: string;
      partner: string;
      step_index: number;
      step_description: string;
      completed: boolean;
      completed_at: string | null;
      notes: string | null;
    }>;
    progress: {
      total: number;
      completed: number;
      percentage: number;
    };
    message?: string;
  } | null;
  onToggleStep: (stepId: string, completed: boolean) => void;
  delay?: number;
}

export const RepairComplianceChecklist: React.FC<RepairComplianceProps> = ({
  data,
  onToggleStep,
  delay = 0,
}) => {
  if (!data?.has_data) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay }}
        className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 rounded-xl bg-indigo-50">
            <ClipboardList size={18} className="text-indigo-500" />
          </div>
          <h3 className="text-base font-semibold text-warmGray-700">Repair Plan Compliance</h3>
        </div>
        <p className="text-sm text-warmGray-400">
          {data?.message || 'No repair plan found for this conflict.'}
        </p>
      </motion.div>
    );
  }

  const { steps, progress } = data;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-indigo-50">
            <ClipboardList size={18} className="text-indigo-500" />
          </div>
          <h3 className="text-base font-semibold text-warmGray-700">Repair Plan Compliance</h3>
        </div>
        <span className="text-sm font-medium text-warmGray-600">
          {progress.completed}/{progress.total}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-warmGray-100 rounded-full overflow-hidden mb-4">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-indigo-400 to-purple-400"
          initial={{ width: 0 }}
          animate={{ width: `${progress.percentage}%` }}
          transition={{ duration: 0.8, delay: delay + 0.2 }}
        />
      </div>
      <p className="text-xs text-warmGray-400 mb-4">
        {progress.percentage}% complete
      </p>

      {/* Steps checklist */}
      <div className="space-y-2">
        {steps.map((step, idx) => (
          <motion.button
            key={step.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.05 * idx }}
            onClick={() => onToggleStep(step.id, !step.completed)}
            className={`w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all hover:bg-warmGray-50/50 ${
              step.completed ? 'opacity-70' : ''
            }`}
          >
            {step.completed ? (
              <CheckCircle2 size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
            ) : (
              <Circle size={20} className="text-warmGray-300 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              <p className={`text-sm ${step.completed ? 'line-through text-warmGray-400' : 'text-warmGray-700'}`}>
                {step.step_description}
              </p>
              {step.completed_at && (
                <p className="text-[10px] text-warmGray-400 mt-0.5">
                  Completed {new Date(step.completed_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
};

export default RepairComplianceChecklist;
