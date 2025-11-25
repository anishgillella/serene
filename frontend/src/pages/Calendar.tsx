import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ChevronLeft, 
  ChevronRight, 
  Plus, 
  Heart, 
  AlertTriangle, 
  Calendar as CalendarIcon,
  Droplet,
  Star,
  Gift,
  Activity
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

const API_BASE = 'http://localhost:8000';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// Event type icons
const getEventIcon = (eventType: string) => {
  switch (eventType) {
    case 'period_start':
    case 'period_end':
      return <Droplet size={12} className="text-pink-500" />;
    case 'ovulation':
    case 'fertile_start':
    case 'fertile_end':
      return <Star size={12} className="text-pink-400" />;
    case 'pms_start':
      return <AlertTriangle size={12} className="text-amber-500" />;
    case 'intimacy':
      return <Heart size={12} className="text-blue-500" />;
    case 'conflict':
      return <AlertTriangle size={12} className="text-red-500" />;
    case 'anniversary':
    case 'birthday':
    case 'first_date':
    case 'milestone':
      return <Gift size={12} className="text-amber-500" />;
    default:
      return <CalendarIcon size={12} className="text-gray-500" />;
  }
};

// Risk level badge
const RiskBadge: React.FC<{ level: string }> = ({ level }) => {
  const colors = {
    high: 'bg-red-100 text-red-700 border-red-200',
    medium: 'bg-amber-100 text-amber-700 border-amber-200',
    low: 'bg-green-100 text-green-700 border-green-200',
    unknown: 'bg-gray-100 text-gray-700 border-gray-200',
  };
  
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${colors[level as keyof typeof colors] || colors.unknown}`}>
      {level.toUpperCase()}
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
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
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
            notes: eventData.notes
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
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-gray-800 flex items-center justify-center gap-2">
          <CalendarIcon size={24} className="text-rose-500" />
          Relationship Calendar
        </h2>
        <p className="text-sm text-gray-600">
          Track cycles, intimacy, conflicts, and special moments
        </p>
      </div>

      {/* Current Cycle Phase Card */}
      {cyclePhase && cyclePhase.phase_name !== 'Unknown' && (
        <div className="bg-gradient-to-r from-pink-50 to-rose-50 rounded-xl p-4 mb-4 border border-pink-100">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg">{cyclePhase.emoji || '📅'}</span>
                <span className="font-medium text-gray-800">{cyclePhase.phase_name}</span>
                <RiskBadge level={cyclePhase.risk_level} />
              </div>
              <p className="text-sm text-gray-600 mt-1">{cyclePhase.description}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-rose-500">Day {cyclePhase.day_of_cycle}</div>
              <div className="text-xs text-gray-500">
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

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        {[
          { key: 'cycle', label: '🩸 Cycle', color: 'bg-pink-100 border-pink-300' },
          { key: 'intimacy', label: '💕 Intimacy', color: 'bg-blue-100 border-blue-300' },
          { key: 'conflict', label: '⚠️ Conflicts', color: 'bg-red-100 border-red-300' },
          { key: 'memorable', label: '🎂 Dates', color: 'bg-amber-100 border-amber-300' },
          { key: 'prediction', label: '🔮 Predictions', color: 'bg-purple-100 border-purple-300' },
        ].map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => setFilters({ ...filters, [key]: !filters[key as keyof typeof filters] })}
            className={`px-3 py-1 text-xs rounded-full border transition-all ${
              filters[key as keyof typeof filters]
                ? color
                : 'bg-gray-50 border-gray-200 opacity-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-soft">
        {/* Day headers */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {DAY_NAMES.map((day) => (
            <div key={day} className="text-center text-xs font-medium text-gray-500 py-1">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar days */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {days.map((day, index) => {
              if (day === null) {
                return <div key={`empty-${index}`} className="h-20" />;
              }
              
              const events = getEventsForDay(day);
              const hasEvents = events.length > 0;
              const hasPeriod = events.some(e => e.event_type === 'period_start' || e.event_type === 'period_end');
              const hasConflict = events.some(e => e.type === 'conflict');
              const hasIntimacy = events.some(e => e.type === 'intimacy');
              const hasMemorable = events.some(e => e.type === 'memorable');
              const hasPrediction = events.some(e => e.is_prediction);
              
              return (
                <div
                  key={day}
                  onClick={() => setSelectedDate(`${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`)}
                  className={`h-20 p-1 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                    isToday(day)
                      ? hasConflict
                        ? 'border-red-400 bg-red-50'
                        : 'border-rose-400 bg-rose-50'
                      : hasEvents
                      ? hasConflict
                        ? 'border-red-200 bg-red-50/30'
                        : 'border-gray-200 bg-white'
                      : 'border-gray-100 bg-gray-50/50'
                  }`}
                >
                  <div className={`text-sm font-medium ${
                    isToday(day)
                      ? hasConflict
                        ? 'text-red-600'
                        : 'text-rose-600'
                      : hasConflict
                      ? 'text-red-600'
                      : 'text-gray-700'
                  }`}>
                    {day}
                    {hasConflict && <span className="text-xs ml-0.5">!</span>}
                  </div>
                  
                  {/* Event indicators - conflicts first */}
                  <div className="flex flex-wrap gap-0.5 mt-1">
                    {hasConflict && (
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500" title="Conflict" />
                    )}
                    {hasPeriod && (
                      <div className="w-2 h-2 rounded-full bg-pink-500" title="Cycle" />
                    )}
                    {hasIntimacy && (
                      <div className="w-2 h-2 rounded-full bg-blue-500" title="Intimacy" />
                    )}
                    {hasMemorable && (
                      <div className="w-2 h-2 rounded-full bg-amber-500" title="Special Date" />
                    )}
                    {hasPrediction && (
                      <div className="w-2 h-2 rounded-full bg-purple-400 opacity-60" title="Prediction" />
                    )}
                  </div>
                  
                  {/* Show conflict first if present, otherwise first event */}
                  {events.length > 0 && (
                    <div className="text-[10px] text-gray-500 truncate mt-1 line-clamp-1">
                      {events.find(e => e.type === 'conflict')?.title.replace(/[📌⚠️]/g, '').trim().substring(0, 12) ||
                       events[0].title.replace(/[📌🩸💕⚠️🎂🔮]/g, '').trim().substring(0, 12)}
                      {events.length > 1 && ` +${events.length - 1}`}
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
        <div className="grid grid-cols-5 gap-2 mt-4">
          <div className="bg-pink-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-pink-600">{calendarData.stats.cycle_events}</div>
            <div className="text-xs text-gray-600">Cycle</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-blue-600">{calendarData.stats.intimacy_events}</div>
            <div className="text-xs text-gray-600">Intimacy</div>
          </div>
          <div className="bg-red-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-red-600">{calendarData.stats.conflict_events}</div>
            <div className="text-xs text-gray-600">Conflicts</div>
          </div>
          <div className="bg-amber-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-amber-600">{calendarData.stats.memorable_events}</div>
            <div className="text-xs text-gray-600">Special</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-purple-600">{calendarData.stats.predictions}</div>
            <div className="text-xs text-gray-600">Predicted</div>
          </div>
        </div>
      )}

      {/* Selected Date Events Panel */}
      {selectedDate && calendarData?.events_by_date[selectedDate] && (
        <div className="fixed inset-0 bg-black/30 flex items-end justify-center z-50" onClick={() => setSelectedDate(null)}>
          <div 
            className="bg-white rounded-t-2xl w-full max-w-lg max-h-[60vh] overflow-y-auto p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-800">
                Events on {new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </h3>
              <button
                onClick={() => setSelectedDate(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-3">
              {calendarData.events_by_date[selectedDate].map((event, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
                    event.type === 'conflict' ? 'cursor-pointer hover:shadow-md' : ''
                  }`}
                  style={{ backgroundColor: `${event.color}15` }}
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
                    className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${event.color}30` }}
                  >
                    {getEventIcon(event.event_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`font-medium ${event.type === 'conflict' ? 'text-gray-800 hover:text-rose-600' : 'text-gray-800'}`}>
                      {event.title}
                      {event.type === 'conflict' && <span className="text-xs ml-2 text-gray-500">→ Click to view</span>}
                    </div>
                    {event.description && (
                      <div className="text-sm text-gray-600 truncate">{event.description}</div>
                    )}
                    {event.is_prediction && event.confidence && (
                      <div className="text-xs text-purple-600 mt-1">
                        Confidence: {Math.round(event.confidence * 100)}%
                      </div>
                    )}
                    {event.status && (
                      <div className="text-xs text-gray-500 mt-1 capitalize">
                        Status: {event.status}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Add Event FAB */}
      <button
        onClick={() => setShowAddModal(true)}
        className="fixed bottom-20 right-4 w-14 h-14 bg-rose-500 hover:bg-rose-600 text-white rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-105"
      >
        <Plus size={24} />
      </button>

      {/* Add Event Modal */}
      {showAddModal && (
        <AddEventModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddEvent}
          eventType={addEventType}
          setEventType={setAddEventType}
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
}

const AddEventModal: React.FC<AddEventModalProps> = ({ onClose, onAdd, eventType, setEventType }) => {
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    cycleType: 'period_start',
    memorableType: 'anniversary',
    title: '',
    notes: '',
    isRecurring: true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-2xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Add Event</h3>
        
        {/* Event Type Tabs */}
        <div className="flex gap-2 mb-4">
          {[
            { key: 'cycle', label: '🩸 Cycle' },
            { key: 'intimacy', label: '💕 Intimacy' },
            { key: 'memorable', label: '🎂 Date' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setEventType(key as 'cycle' | 'intimacy' | 'memorable')}
              className={`flex-1 py-2 text-sm rounded-lg transition-all ${
                eventType === key
                  ? 'bg-rose-100 text-rose-700 border border-rose-300'
                  : 'bg-gray-50 text-gray-600 border border-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-transparent"
              required
            />
          </div>

          {/* Cycle Type */}
          {eventType === 'cycle' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
              <select
                value={formData.cycleType}
                onChange={(e) => setFormData({ ...formData, cycleType: e.target.value })}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-transparent"
              >
                <option value="period_start">Period Started</option>
                <option value="period_end">Period Ended</option>
                <option value="ovulation">Ovulation</option>
                <option value="pms_start">PMS Started</option>
              </select>
            </div>
          )}

          {/* Memorable Type */}
          {eventType === 'memorable' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
                <select
                  value={formData.memorableType}
                  onChange={(e) => setFormData({ ...formData, memorableType: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-transparent"
                >
                  <option value="anniversary">Anniversary</option>
                  <option value="birthday">Birthday</option>
                  <option value="first_date">First Date</option>
                  <option value="milestone">Milestone</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., First Anniversary"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-transparent"
                  required
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="recurring"
                  checked={formData.isRecurring}
                  onChange={(e) => setFormData({ ...formData, isRecurring: e.target.checked })}
                  className="rounded text-rose-500 focus:ring-rose-500"
                />
                <label htmlFor="recurring" className="text-sm text-gray-700">Repeat yearly</label>
              </div>
            </>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Add any notes..."
              rows={2}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-2 bg-rose-500 text-white rounded-lg hover:bg-rose-600 transition-colors"
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

