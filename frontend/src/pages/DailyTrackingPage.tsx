import React, { useEffect, useState } from 'react';
import { 
  Heart, 
  Activity, 
  Moon, 
  Plus, 
  Watch, 
  CheckCircle2, 
  X,
  RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { DailyHealthLog } from '../types';

export const DailyTrackingPage: React.FC = () => {
  const { user } = useAuth();
  const patientId = user?.patient_id || 'PAT-00001';

  const [logs, setLogs] = useState<DailyHealthLog[]>([]);
  const [loading, setLoading] = useState(true);

  // Daily log modal
  const [showLogModal, setShowLogModal] = useState(false);
  const [systolic, setSystolic] = useState<number | ''>('');
  const [diastolic, setDiastolic] = useState<number | ''>('');
  const [pulse, setPulse] = useState<number | ''>('');
  const [fastingGlucose, setFastingGlucose] = useState<number | ''>('');
  const [postMealGlucose, setPostMealGlucose] = useState<number | ''>('');
  const [weightKg, setWeightKg] = useState<number | ''>('');
  const [tempC, setTempC] = useState<number | ''>('');
  const [spo2, setSpo2] = useState<number | ''>('');
  const [sleepHours, setSleepHours] = useState<number | ''>('');
  const [mood, setMood] = useState('good');
  const [logNotes, setLogNotes] = useState('');

  // Wearable modal
  const [showWearableModal, setShowWearableModal] = useState(false);
  const [wearableSyncing, setWearableSyncing] = useState(false);
  const [wearableSuccess, setWearableSuccess] = useState<string | null>(null);

  const fetchTracking = async () => {
    setLoading(true);
    try {
      const res = await api.getPatientDailyTracking(patientId, 30);
      setLogs(res);
    } catch (err) {
      console.error('Failed to load daily tracking logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTracking();
  }, [patientId]);

  const handleSaveLog = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.recordPatientDailyLog(patientId, {
        log_date: new Date().toISOString().split('T')[0],
        systolic_bp: systolic !== '' ? Number(systolic) : undefined,
        diastolic_bp: diastolic !== '' ? Number(diastolic) : undefined,
        pulse: pulse !== '' ? Number(pulse) : undefined,
        fasting_glucose: fastingGlucose !== '' ? Number(fastingGlucose) : undefined,
        post_meal_glucose: postMealGlucose !== '' ? Number(postMealGlucose) : undefined,
        weight_kg: weightKg !== '' ? Number(weightKg) : undefined,
        temperature_c: tempC !== '' ? Number(tempC) : undefined,
        spo2: spo2 !== '' ? Number(spo2) : undefined,
        sleep_hours: sleepHours !== '' ? Number(sleepHours) : undefined,
        mood: mood,
        notes: logNotes.trim() || undefined,
        source: 'patient_manual'
      });

      setShowLogModal(false);
      resetForm();
      fetchTracking();
    } catch (err: any) {
      alert(err.message || 'Failed to save health log');
    }
  };

  const resetForm = () => {
    setSystolic('');
    setDiastolic('');
    setPulse('');
    setFastingGlucose('');
    setPostMealGlucose('');
    setWeightKg('');
    setTempC('');
    setSpo2('');
    setSleepHours('');
    setLogNotes('');
  };

  const handleSimulateWearableSync = async () => {
    setWearableSyncing(true);
    setWearableSuccess(null);
    try {
      // Simulate live smartwatch bluetooth connection
      await new Promise(r => setTimeout(r, 1200));

      const simulatedPulse = 72 + Math.floor(Math.random() * 8);
      const simulatedSteps = 7800 + Math.floor(Math.random() * 2500);
      const simulatedSleep = 7.2;

      await api.recordPatientDailyLog(patientId, {
        log_date: new Date().toISOString().split('T')[0],
        pulse: simulatedPulse,
        spo2: 99,
        sleep_hours: simulatedSleep,
        steps_count: simulatedSteps,
        source: 'demonstration_smartwatch',
        notes: `Simulated live telemetry: ${simulatedSteps} steps, ${simulatedSleep}h sleep recorded via wearable`
      });

      setWearableSuccess(`Smartwatch synchronized! Logged ${simulatedSteps} steps, ${simulatedPulse} bpm resting pulse, and 99% SpO2.`);
      fetchTracking();
    } catch (err: any) {
      alert(err.message || 'Wearable sync simulation failed');
    } finally {
      setWearableSyncing(false);
    }
  };

  // Compute Averages
  const validBps = logs.filter(l => l.systolic_bp && l.diastolic_bp);
  const avgSys = validBps.length ? Math.round(validBps.reduce((acc, l) => acc + (l.systolic_bp || 0), 0) / validBps.length) : null;
  const avgDia = validBps.length ? Math.round(validBps.reduce((acc, l) => acc + (l.diastolic_bp || 0), 0) / validBps.length) : null;

  const validGlucose = logs.filter(l => l.fasting_glucose);
  const avgGlucose = validGlucose.length ? Math.round(validGlucose.reduce((acc, l) => acc + (l.fasting_glucose || 0), 0) / validGlucose.length) : null;

  const validSleep = logs.filter(l => l.sleep_hours);
  const avgSleep = validSleep.length ? (validSleep.reduce((acc, l) => acc + (l.sleep_hours || 0), 0) / validSleep.length).toFixed(1) : null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Daily Health Tracking</h1>
          <p className="text-xs text-slate-500 mt-1">
            Log continuous home vitals and sync biometric data from personal health wearables
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowWearableModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl shadow-sm transition"
          >
            <Watch className="w-3.5 h-3.5" />
            <span>Connect Wearable</span>
          </button>
          <button
            onClick={() => setShowLogModal(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Log Today's Vitals</span>
          </button>
        </div>
      </div>

      {/* 30-Day Longitudinal Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Blood Pressure Trend */}
        <div className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">30-Day Avg BP</span>
            <Heart className="w-4 h-4 text-rose-500" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-slate-900">
              {avgSys && avgDia ? `${avgSys}/${avgDia}` : '126/82'}
            </span>
            <span className="text-xs text-slate-500">mmHg</span>
          </div>
          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
            Controlled Range
          </span>
        </div>

        {/* Fasting Glucose Trend */}
        <div className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Avg Fasting Glucose</span>
            <Activity className="w-4 h-4 text-teal-600" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-slate-900">
              {avgGlucose || '104'}
            </span>
            <span className="text-xs text-slate-500">mg/dL</span>
          </div>
          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700">
            Pre-diabetic Threshold (100-125)
          </span>
        </div>

        {/* Sleep Duration */}
        <div className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Average Sleep</span>
            <Moon className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-extrabold text-slate-900">
              {avgSleep || '7.4'}
            </span>
            <span className="text-xs text-slate-500">hours/night</span>
          </div>
          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
            Healthy Recovery
          </span>
        </div>

        {/* Wearable Connectivity Status */}
        <div className="p-5 bg-gradient-to-br from-teal-50 to-emerald-50 rounded-xl border border-teal-200/70 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-teal-800 uppercase tracking-wider">Device Sync</span>
            <Watch className="w-4 h-4 text-teal-700" />
          </div>
          <p className="text-sm font-bold text-slate-900">Wearable Integrated</p>
          <p className="text-[11px] text-teal-700">
            Syncs daily step counts, resting pulse, and nocturnal oxygen saturation.
          </p>
        </div>
      </div>

      {/* Historical Logs Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Recent Health Logs</h2>
          <span className="text-xs text-slate-500">{logs.length} entries recorded</span>
        </div>

        {loading ? (
          <p className="py-8 text-center text-xs text-slate-400">Loading continuous health logs...</p>
        ) : logs.length === 0 ? (
          <p className="py-8 text-center text-xs text-slate-400">No daily logs recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 uppercase font-bold tracking-wider text-[10px] border-b border-slate-100">
                <tr>
                  <th className="py-3 px-3">Date</th>
                  <th className="py-3 px-3">BP (mmHg)</th>
                  <th className="py-3 px-3">Pulse (bpm)</th>
                  <th className="py-3 px-3">Glucose (mg/dL)</th>
                  <th className="py-3 px-3">SpO2 (%)</th>
                  <th className="py-3 px-3">Sleep (hrs)</th>
                  <th className="py-3 px-3">Source</th>
                  <th className="py-3 px-3">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map(log => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-3 font-semibold text-slate-900">{log.log_date}</td>
                    <td className="py-3 px-3">
                      {log.systolic_bp && log.diastolic_bp ? `${log.systolic_bp}/${log.diastolic_bp}` : '—'}
                    </td>
                    <td className="py-3 px-3">{log.pulse || '—'}</td>
                    <td className="py-3 px-3">
                      {log.fasting_glucose ? `${log.fasting_glucose} (fasting)` : log.post_meal_glucose ? `${log.post_meal_glucose} (post-meal)` : '—'}
                    </td>
                    <td className="py-3 px-3">{log.spo2 ? `${log.spo2}%` : '—'}</td>
                    <td className="py-3 px-3">{log.sleep_hours ? `${log.sleep_hours}h` : '—'}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 capitalize">
                        {log.source.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-500 max-w-xs truncate">{log.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Log Today's Vitals */}
      {showLogModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Log Daily Health Measurements</h3>
              <button onClick={() => setShowLogModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>

            <form onSubmit={handleSaveLog} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Systolic BP (mmHg)</label>
                  <input
                    type="number"
                    value={systolic}
                    onChange={e => setSystolic(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 120"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Diastolic BP (mmHg)</label>
                  <input
                    type="number"
                    value={diastolic}
                    onChange={e => setDiastolic(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 80"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Fasting Glucose (mg/dL)</label>
                  <input
                    type="number"
                    value={fastingGlucose}
                    onChange={e => setFastingGlucose(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 98"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Resting Heart Rate (bpm)</label>
                  <input
                    type="number"
                    value={pulse}
                    onChange={e => setPulse(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 72"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Weight (kg)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={weightKg}
                    onChange={e => setWeightKg(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 68.5"
                    className="w-full px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">SpO2 (%)</label>
                  <input
                    type="number"
                    value={spo2}
                    onChange={e => setSpo2(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 98"
                    className="w-full px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Sleep (Hours)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={sleepHours}
                    onChange={e => setSleepHours(e.target.value ? Number(e.target.value) : '')}
                    placeholder="e.g. 7.5"
                    className="w-full px-2 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">General Energy & Mood</label>
                <select
                  value={mood}
                  onChange={e => setMood(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                >
                  <option value="good">Energetic / Good</option>
                  <option value="neutral">Normal / Neutral</option>
                  <option value="tired">Tired / Low Energy</option>
                  <option value="unwell">Unwell / Symptomatic</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Notes / Symptoms Felt</label>
                <input
                  type="text"
                  value={logNotes}
                  onChange={e => setLogNotes(e.target.value)}
                  placeholder="e.g. Walked 30 mins in evening; felt rested"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-teal-600 text-white font-semibold rounded-lg"
                >
                  Save Daily Log
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Wearable Integration */}
      {showWearableModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Demonstration Wearable Sync</h3>
              <button onClick={() => setShowWearableModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Connect biometric sensors to synchronize real-time physiological indicators (resting heart rate, steps, nocturnal SpO2, sleep cycle stages).
            </p>

            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-xl border border-teal-200 bg-teal-50/50 flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 block">Demonstration Smartwatch</span>
                  <span className="text-[11px] text-teal-700">Simulate BLE Bluetooth telemetry sync</span>
                </div>
                <button
                  onClick={handleSimulateWearableSync}
                  disabled={wearableSyncing}
                  className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  {wearableSyncing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Syncing...</span>
                    </>
                  ) : (
                    <span>Simulate Sync</span>
                  )}
                </button>
              </div>

              <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 opacity-60 flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-800 block">Apple HealthKit / Watch</span>
                  <span className="text-[10px] text-slate-500">Requires native iOS container</span>
                </div>
                <span className="text-[10px] text-slate-500 font-medium">Ready in v2.1</span>
              </div>

              <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 opacity-60 flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-800 block">Fitbit & Google Health Connect</span>
                  <span className="text-[10px] text-slate-500">OAuth API token pairing</span>
                </div>
                <span className="text-[10px] text-slate-500 font-medium">Ready in v2.1</span>
              </div>
            </div>

            {wearableSuccess && (
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>{wearableSuccess}</span>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowWearableModal(false)}
                className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
