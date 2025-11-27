import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Calendar as CalendarIcon
} from 'lucide-react';

// Types
interface CalendarEvent {
  id: string;
  type: 'cycle' | 'intimacy' | 'conflict' | 'memorable' | 'prediction';
  event_type: string;
  event_date?: string;
  predicted_date?: string;
  title: string;
  description?: string;
  color: string;
  is_prediction?: boolean;
  confidence?: number;
  risk_level?: string;
  phase_name?: string;
  status?: string;
}

interface CyclePhase {
  phase_name: string;
  day_of_cycle: number | null;
  days_until_period: number | null;
  risk_level: string;
  description: string;
  emoji?: string;
  confidence: number;
}

interface CalendarData {
  year: number;
  month: number;
  events: CalendarEvent[];
  events_by_date: Record<string, CalendarEvent[]>;
  stats: {
    total_events: number;
    cycle_events: number;
    intimacy_events: number;
    conflict_events: number;
    memorable_events: number;
    predictions: number;
  };
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// Event type icons - Sleek emoji-based system
const getEventIcon = (eventType: string) => {
  const iconMap: Record<string, string> = {
    // Cycle events
    'period_start': '🌸',
    'period_end': '🌸',
    'ovulation': '✨',
    'fertile_start': '🌺',
    'fertile_end': '🌺',
    'pms_start': '💫',
    'symptom_log': '📝',
    'mood_log': '😊',

    // Intimacy
    'intimacy': '💝',

    // Conflicts
    'conflict': '⚡',

    // Memorable dates
    'anniversary': '💍',
    'birthday': '🎂',
    'first_date': '💕',
    'milestone': '🏆',
    'holiday': '🎉',
    'custom': '⭐',

    // Social & Activities
    'social': '👥',
    'trip': '✈️',
    'event': '🎭',
    'appointment': '📅',
    'work': '💼',
  };

  const emoji = iconMap[eventType] || '📌';
  return <span className="text-sm">{emoji}</span>;
};

// Risk level badge
const RiskBadge: React.FC<{ level: string }> = ({ level }) => {
  const colors = {
    high: 'bg-rose-50 text-rose-700 border-rose-100',
    medium: 'bg-amber-50 text-amber-700 border-amber-100',
    low: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    unknown: 'bg-surface-hover text-text-tertiary border-border-subtle',
  };

  return (
    <span className={`text-tiny px-2.5 py-0.5 rounded-full border font-medium uppercase tracking-wider ${colors[level as keyof typeof colors] || colors.unknown}`}>
      {level}
    </span>
  );
};

const Calendar: React.FC = () => {
  const today = new Date();
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1);
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [cyclePhase, setCyclePhase] = useState<CyclePhase | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    cycle: true,
    intimacy: true,
    conflict: true,
    memorable: true,
    prediction: true,
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [addEventType, setAddEventType] = useState<'cycle' | 'intimacy' | 'memorable'>('cycle');
  const [initialAddDate, setInitialAddDate] = useState<string | undefined>(undefined);
  const navigate = useNavigate();

  // Fetch calendar data
  useEffect(() => {
    const fetchCalendarData = async () => {
      setLoading(true);
      try {
        const activeFilters = Object.entries(filters)
          .filter(([, v]) => v)
          .map(([k]) => k)
          .join(',');

        const [calendarRes, phaseRes] = await Promise.all([
          fetch(`${API_BASE}/api/calendar/events?year=${currentYear}&month=${currentMonth}&filters=${activeFilters}`),
          fetch(`${API_BASE}/api/calendar/cycle-phase?partner_id=partner_b`)
        ]);

        if (calendarRes.ok) {
          const data = await calendarRes.json();
          setCalendarData(data);
        }

        if (phaseRes.ok) {
          const phase = await phaseRes.json();
          setCyclePhase(phase);
        }
      } catch (error) {
        console.error('Error fetching calendar data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCalendarData();
  }, [currentYear, currentMonth, filters]);

  // Generate calendar grid
  const generateCalendarDays = () => {
    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const startingDayOfWeek = firstDay.getDay();
    const daysInMonth = lastDay.getDate();

    const days: (number | null)[] = [];

    // Add empty cells for days before the first of the month
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }

    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day);
    }

    return days;
  };

  const getEventsForDay = (day: number): CalendarEvent[] => {
    if (!calendarData) return [];
    const dateStr = `${currentYear} -${String(currentMonth).padStart(2, '0')} -${String(day).padStart(2, '0')} `;
    return calendarData.events_by_date[dateStr] || [];
  };

  const isToday = (day: number): boolean => {
    return (
      day === today.getDate() &&
      currentMonth === today.getMonth() + 1 &&
      currentYear === today.getFullYear()
    );
  };

  const navigateMonth = (delta: number) => {
    let newMonth = currentMonth + delta;
    let newYear = currentYear;

    if (newMonth > 12) {
      newMonth = 1;
      newYear++;
    } else if (newMonth < 1) {
      newMonth = 12;
      newYear--;
    }

    setCurrentMonth(newMonth);
    setCurrentYear(newYear);
  };

  const handleAddEvent = async (eventData: any) => {
    try {
      let endpoint = '';
      let body = {};

      switch (addEventType) {
        case 'cycle':
          endpoint = '/api/calendar/cycle-events';
          body = {
            partner_id: 'partner_b',
            event_type: eventData.cycleType,
            event_date: eventData.date,
            notes: eventData.notes,
            symptoms: eventData.symptoms || []
          };
          break;
        case 'intimacy':
          endpoint = '/api/calendar/intimacy-events';
          body = {
            event_date: eventData.date,
            notes: eventData.notes
          };
          break;
        case 'memorable':
          endpoint = '/api/calendar/memorable-dates';
          body = {
            title: eventData.title,
            event_date: eventData.date,
            event_type: eventData.memorableType,
            description: eventData.notes,
            is_recurring: eventData.isRecurring
          };
          break;
      }

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (res.ok) {
        // Refresh calendar data
        setFilters({ ...filters });
        setShowAddModal(false);
      }
    } catch (error) {
      console.error('Error adding event:', error);
    }
  };

  const days = generateCalendarDays();

  return (
    <div className="py-4 max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-h2 text-text-primary flex items-center justify-center gap-3 mb-2">
          <CalendarIcon size={24} className="text-accent" strokeWidth={1.5} />
          Relationship Calendar
        </h2>
        <p className="text-body text-text-secondary">
          Track cycles, intimacy, conflicts, and special moments
        </p>
      </div>

      {/* Current Cycle Phase Card */}
      {cyclePhase && cyclePhase.phase_name !== 'Unknown' && (
        <div className="bg-surface-elevated rounded-xl p-6 mb-8 border border-border-subtle shadow-soft">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{cyclePhase.emoji || '📅'}</span>
                <span className="text-h3 text-text-primary">{cyclePhase.phase_name}</span>
                <RiskBadge level={cyclePhase.risk_level} />
              </div>
              <p className="text-body text-text-secondary">{cyclePhase.description}</p>
            </div>
            <div className="text-right">
              <div className="text-h2 text-accent mb-1">Day {cyclePhase.day_of_cycle}</div>
              <div className="text-small text-text-tertiary">
                {cyclePhase.days_until_period !== null && cyclePhase.days_until_period > 0
                  ? `${cyclePhase.days_until_period} days until period`
                  : ''}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Month Navigation */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => navigateMonth(-1)}
          className="p-2 hover:bg-gray-100 rounded-full transition-colors"
        >
          <ChevronLeft size={20} />
        </button>
        <h3 className="text-lg font-semibold text-gray-800">
          {MONTH_NAMES[currentMonth - 1]} {currentYear}
        </h3>
        <button
          onClick={() => navigateMonth(1)}
          className="p-2 hover:bg-gray-100 rounded-full transition-colors"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Event Legend - Sleek and Prominent */}
      <div className="bg-surface-elevated rounded-xl p-5 mb-6 border border-border-subtle shadow-soft">
        <h3 className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-3">Event Types</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { key: 'cycle', label: 'Cycle', icon: '🌸', color: 'bg-rose-100 text-rose-600' },
            { key: 'intimacy', label: 'Intimacy', icon: '💝', color: 'bg-pink-100 text-pink-600' },
            { key: 'conflict', label: 'Conflicts', icon: '⚡', color: 'bg-amber-100 text-amber-600' },
            { key: 'memorable', label: 'Special', icon: '✨', color: 'bg-purple-100 text-purple-600' },
            { key: 'prediction', label: 'Forecast', icon: '🔮', color: 'bg-indigo-100 text-indigo-600' },
          ].map(({ key, label, icon, color }) => (
            <button
              key={key}
              onClick={() => setFilters({ ...filters, [key]: !filters[key as keyof typeof filters] })}
              className={`px-3 py-2.5 rounded-lg border-2 transition-all flex items-center gap-2 font-medium ${filters[key as keyof typeof filters]
                ? `${color} border-current shadow-sm scale-105`
                : 'bg-white border-border-subtle text-text-tertiary opacity-60 hover:opacity-100'
                }`}
            >
              <span className="text-lg">{icon}</span>
              <span className="text-small">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-surface-elevated rounded-xl p-6 shadow-soft border border-border-subtle">
        {/* Day headers */}
        <div className="grid grid-cols-7 gap-1 mb-4">
          {DAY_NAMES.map((day) => (
            <div key={day} className="text-center text-tiny font-medium text-text-tertiary uppercase tracking-wider py-1">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar days */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {days.map((day, index) => {
              if (day === null) {
                return <div key={`empty-${index}`} className="h-24" />;
              }

              const events = getEventsForDay(day);
              const hasEvents = events.length > 0;
              const hasConflict = events.some(e => e.type === 'conflict');

              // Group events by type
              const groupedEvents = events.reduce((acc, event) => {
                const key = event.event_type;
                if (!acc[key]) {
                  acc[key] = [];
                }
                acc[key].push(event);
                return acc;
              }, {} as Record<string, CalendarEvent[]>);

              const eventGroups = Object.values(groupedEvents);

              return (
                <div
                  key={day}
                  onClick={() => setSelectedDate(`${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`)}
                  className={`h-24 p-2 rounded-lg border transition-all cursor-pointer hover:shadow-subtle group ${isToday(day)
                    ? 'border-accent bg-surface-hover'
                    : hasEvents
                      ? 'border-border-subtle bg-surface-elevated hover:border-border-medium'
                      : 'border-transparent hover:bg-surface-hover'
                    }`}
                >
                  <div className={`text-small font-medium mb-1 flex justify-between items-start ${isToday(day)
                    ? 'text-accent'
                    : 'text-text-secondary group-hover:text-text-primary'
                    }`}>
                    <span>{day}</span>
                    {hasConflict && <span className="text-red-500 text-xs">!</span>}
                  </div>

                  {/* Event indicators - sleek emoji badges with counts */}
                  <div className="flex flex-wrap gap-1 mb-1 min-h-[16px]">
                    {eventGroups.slice(0, 3).map((group, idx) => {
                      const firstEvent = group[0];
                      const count = group.length;

                      return (
                        <div
                          key={idx}
                          className="relative group/badge"
                          title={`${count} ${firstEvent.event_type.replace('_', ' ')} event${count > 1 ? 's' : ''}`}
                        >
                          <div className="w-5 h-5 flex items-center justify-center text-[10px] bg-white rounded-full shadow-sm border border-border-subtle">
                            {getEventIcon(firstEvent.event_type)}
                          </div>
                          {count > 1 && (
                            <div className="absolute -top-1 -right-1 w-3 h-3 bg-accent text-white text-[8px] flex items-center justify-center rounded-full border border-white font-bold">
                              {count}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {eventGroups.length > 3 && (
                      <div className="w-5 h-5 flex items-center justify-center text-[9px] font-medium bg-accent/10 text-accent rounded-full border border-accent/20">
                        +{eventGroups.length - 3}
                      </div>
                    )}
                  </div>

                  {/* Show conflict first if present, otherwise first event */}
                  {events.length > 0 && (
                    <div className="text-[10px] text-text-tertiary truncate leading-tight">
                      {events.find(e => e.type === 'conflict')?.title.replace(/[📌⚠️]/g, '').trim().substring(0, 12) ||
                        events[0].title.replace(/[📌🩸💕⚠️🎂🔮]/g, '').trim().substring(0, 12)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Stats Summary */}
      {calendarData && (
        <div className="grid grid-cols-5 gap-4 mt-8">
          <div className="bg-surface-elevated rounded-xl p-4 text-center border border-border-subtle shadow-soft">
            <div className="text-h3 text-pink-500 mb-1">{calendarData.stats.cycle_events}</div>
            <div className="text-tiny text-text-tertiary uppercase tracking-wider">Cycle</div>
          </div>
          <div className="bg-surface-elevated rounded-xl p-4 text-center border border-border-subtle shadow-soft">
            <div className="text-h3 text-blue-500 mb-1">{calendarData.stats.intimacy_events}</div>
            <div className="text-tiny text-text-tertiary uppercase tracking-wider">Intimacy</div>
          </div>
          <div className="bg-surface-elevated rounded-xl p-4 text-center border border-border-subtle shadow-soft">
            <div className="text-h3 text-red-500 mb-1">{calendarData.stats.conflict_events}</div>
            <div className="text-tiny text-text-tertiary uppercase tracking-wider">Conflicts</div>
          </div>
          <div className="bg-surface-elevated rounded-xl p-4 text-center border border-border-subtle shadow-soft">
            <div className="text-h3 text-amber-500 mb-1">{calendarData.stats.memorable_events}</div>
            <div className="text-tiny text-text-tertiary uppercase tracking-wider">Special</div>
          </div>
          <div className="bg-surface-elevated rounded-xl p-4 text-center border border-border-subtle shadow-soft">
            <div className="text-h3 text-purple-500 mb-1">{calendarData.stats.predictions}</div>
            <div className="text-tiny text-text-tertiary uppercase tracking-wider">Predicted</div>
          </div>
        </div>
      )}

      {/* Selected Date Events Panel */}
      {selectedDate && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-end justify-center z-50" onClick={() => setSelectedDate(null)}>
          <div
            className="bg-surface-elevated rounded-t-3xl w-full max-w-lg max-h-[70vh] overflow-y-auto p-6 shadow-lifted animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-h3 text-text-primary">
                Events on {new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </h3>
              <button
                onClick={() => setSelectedDate(null)}
                className="p-2 hover:bg-surface-hover rounded-full transition-colors text-text-tertiary hover:text-text-primary"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              {(!calendarData?.events_by_date[selectedDate] || calendarData.events_by_date[selectedDate].length === 0) && (
                <div className="text-center py-12 text-text-tertiary">
                  <p>No events for this day</p>
                </div>
              )}

              {calendarData?.events_by_date[selectedDate]?.map((event, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-4 p-4 rounded-xl transition-all border border-transparent ${event.type === 'conflict' ? 'cursor-pointer hover:bg-surface-hover hover:border-border-subtle' : 'bg-surface-hover'
                    }`}
                  onClick={() => {
                    if (event.type === 'conflict' && event.id) {
                      setSelectedDate(null);
                      navigate('/post-fight', {
                        state: {
                          conflict_id: event.id,
                          conflict_date: event.event_date
                        }
                      });
                    }
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-white border border-border-subtle shadow-soft"
                  >
                    {getEventIcon(event.event_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`text-body font-medium ${event.type === 'conflict' ? 'text-text-primary hover:text-accent' : 'text-text-primary'}`}>
                      {event.title}
                      {event.type === 'conflict' && <span className="text-tiny ml-2 text-text-tertiary">→ View details</span>}
                    </div>
                    {event.description && (
                      <div className="text-small text-text-secondary truncate mt-0.5">{event.description}</div>
                    )}
                    {event.is_prediction && event.confidence && (
                      <div className="text-tiny text-accent mt-1">
                        Confidence: {Math.round(event.confidence * 100)}%
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={() => {
                setInitialAddDate(selectedDate);
                setSelectedDate(null);
                setShowAddModal(true);
              }}
              className="w-full mt-6 py-3.5 bg-white border border-accent text-accent rounded-xl font-medium hover:bg-surface-hover transition-all flex items-center justify-center gap-2"
            >
              <Plus size={20} />
              Add Event
            </button>
          </div>
        </div>
      )}

      {/* Add Event FAB */}
      <button
        onClick={() => {
          setInitialAddDate(undefined);
          setShowAddModal(true);
        }}
        className="fixed bottom-8 right-8 w-14 h-14 bg-white border border-border-subtle hover:border-accent text-accent rounded-full shadow-cozy flex items-center justify-center transition-all hover:scale-105 hover:shadow-lifted z-40"
      >
        <Plus size={24} strokeWidth={1.5} />
      </button>

      {/* Add Event Modal */}
      {showAddModal && (
        <AddEventModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddEvent}
          eventType={addEventType}
          setEventType={setAddEventType}
          initialDate={initialAddDate}
        />
      )}
    </div>
  );
};

// Add Event Modal Component
interface AddEventModalProps {
  onClose: () => void;
  onAdd: (data: any) => void;
  eventType: 'cycle' | 'intimacy' | 'memorable';
  setEventType: (type: 'cycle' | 'intimacy' | 'memorable') => void;
  initialDate?: string;
}

const AddEventModal: React.FC<AddEventModalProps> = ({ onClose, onAdd, eventType, setEventType, initialDate }) => {
  const [formData, setFormData] = useState({
    date: initialDate || new Date().toISOString().split('T')[0],
    cycleType: 'period_start',
    memorableType: 'anniversary',
    title: '',
    notes: '',
    isRecurring: true,
    symptoms: [] as string[],
  });

  const commonSymptoms = [
    'cramps', 'headache', 'mood_swings', 'fatigue',
    'bloating', 'acne', 'breast_tenderness', 'nausea',
    'back_pain', 'irritability', 'anxiety', 'food_cravings'
  ];

  const toggleSymptom = (symptom: string) => {
    setFormData({
      ...formData,
      symptoms: formData.symptoms.includes(symptom)
        ? formData.symptoms.filter(s => s !== symptom)
        : [...formData.symptoms, symptom]
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-surface-elevated rounded-2xl w-full max-w-md max-h-[80vh] overflow-y-auto p-8 shadow-lifted animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-h3 text-text-primary mb-6">Add Event</h3>

        {/* Event Type Tabs */}
        <div className="flex gap-2 mb-6 bg-surface-hover p-1 rounded-xl">
          {[
            { key: 'cycle', label: 'Cycle' },
            { key: 'intimacy', label: 'Intimacy' },
            { key: 'memorable', label: 'Date' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setEventType(key as 'cycle' | 'intimacy' | 'memorable')}
              className={`flex-1 py-2 text-small font-medium rounded-lg transition-all ${eventType === key
                ? 'bg-white text-text-primary shadow-soft'
                : 'text-text-tertiary hover:text-text-secondary'
                }`}
            >
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Date */}
          <div>
            <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none"
              required
            />
          </div>

          {/* Cycle Type */}
          {eventType === 'cycle' && (
            <>
              <div>
                <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Event Type</label>
                <select
                  value={formData.cycleType}
                  onChange={(e) => setFormData({ ...formData, cycleType: e.target.value })}
                  className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none appearance-none"
                >
                  <option value="period_start">Period Started</option>
                  <option value="period_end">Period Ended</option>
                  <option value="symptom_log">Symptom Log</option>
                  <option value="mood_log">Mood Log</option>
                </select>
              </div>

              {/* Symptoms Selector */}
              <div>
                <label className="block text-tiny font-medium text-text-secondary mb-2 uppercase tracking-wider">Symptoms</label>
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-2 border border-border-subtle rounded-xl">
                  {commonSymptoms.map((symptom) => (
                    <label
                      key={symptom}
                      className="flex items-center gap-2 cursor-pointer hover:bg-surface-hover p-2 rounded-lg transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={formData.symptoms.includes(symptom)}
                        onChange={() => toggleSymptom(symptom)}
                        className="rounded text-accent focus:ring-accent border-border-medium"
                      />
                      <span className="text-small text-text-secondary capitalize">
                        {symptom.replace('_', ' ')}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Memorable Type */}
          {eventType === 'memorable' && (
            <>
              <div>
                <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Event Type</label>
                <select
                  value={formData.memorableType}
                  onChange={(e) => setFormData({ ...formData, memorableType: e.target.value })}
                  className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none appearance-none"
                >
                  <option value="anniversary">Anniversary</option>
                  <option value="birthday">Birthday</option>
                  <option value="first_date">First Date</option>
                  <option value="milestone">Milestone</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div>
                <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., First Anniversary"
                  className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none"
                  required
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="recurring"
                  checked={formData.isRecurring}
                  onChange={(e) => setFormData({ ...formData, isRecurring: e.target.checked })}
                  className="rounded text-accent focus:ring-accent border-border-medium"
                />
                <label htmlFor="recurring" className="text-small text-text-secondary">Repeat yearly</label>
              </div>
            </>
          )}

          {/* Notes */}
          <div>
            <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Notes (optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Add any notes..."
              rows={3}
              className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none resize-none"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 border border-border-subtle rounded-xl text-text-secondary hover:bg-surface-hover transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-3 bg-text-primary text-white rounded-xl hover:bg-black transition-colors font-medium shadow-soft"
            >
              Add Event
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Calendar;

