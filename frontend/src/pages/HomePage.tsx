import React, { useEffect, useState } from 'react';
import { 
  Activity, 
  Pill, 
  AlertCircle, 
  MessageSquare, 
  Sparkles, 
  PlusCircle, 
  CheckCircle2, 
  ShieldAlert,
  ArrowRight,
  Building2,
  Stethoscope,
  HeartPulse,
  Receipt,
  FileText
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { Patient, Condition, Medication, Allergy, DailyHealthLog } from '../types';

interface HomePageProps {
  onNavigate: (tab: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  const { user } = useAuth();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [latestLog, setLatestLog] = useState<DailyHealthLog | null>(null);
  const [loading, setLoading] = useState(true);

  const patientId = user?.role === 'patient' ? (user?.patient_id || 'PAT-AARAV-001') : null;

  useEffect(() => {
    let isMounted = true;
    if (!patientId) {
      setLoading(false);
      return;
    }
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const [pat, conds, meds, allgs, tracking] = await Promise.allSettled([
          api.getPatient(patientId),
          api.getPatientConditions(patientId),
          api.getPatientMedications(patientId),
          api.getPatientAllergies(patientId),
          api.getPatientDailyTracking(patientId, 1)
        ]);

        if (!isMounted) return;

        if (pat.status === 'fulfilled') setPatient(pat.value);
        if (conds.status === 'fulfilled') setConditions(conds.value.filter(c => c.clinical_status === 'active'));
        if (meds.status === 'fulfilled') setMedications(meds.value.filter(m => m.status === 'active'));
        if (allgs.status === 'fulfilled') setAllergies(allgs.value);
        if (tracking.status === 'fulfilled' && tracking.value.length > 0) {
          setLatestLog(tracking.value[0]);
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchDashboardData();
    return () => { isMounted = false; };
  }, [patientId]);

  const activeMedCount = medications.length;
  const activeConditionCount = conditions.length;
  const allergyCount = allergies.length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Welcome Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-teal-700 via-teal-600 to-emerald-600 text-white p-6 sm:p-8 shadow-lg">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-sm text-teal-100 text-xs font-medium mb-3">
            <span className="w-2 h-2 rounded-full bg-emerald-300 animate-pulse"></span>
            <span>
              {user?.role === 'patient' 
                ? `Personal Health Portal · ${patientId}` 
                : `${user?.role === 'doctor' ? 'Physician Clinical Station' : user?.role === 'nurse' ? 'Inpatient Nursing Station' : 'Hospital Workspace'} · ${(user as any)?.facility || 'Seth GS Medical College & KEM Hospital'}`}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Welcome back, {user?.full_name || (patient?.first_name ? `${patient.first_name} ${patient.last_name}` : 'Patient')}!
          </h1>
          <p className="mt-2 text-teal-100 text-sm leading-relaxed">
            Your connected longitudinal health record is synchronized. Track daily measurements, review your care routines, or consult with your AI Health Assistant.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate('assistant')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white text-teal-800 text-sm font-semibold rounded-xl shadow hover:bg-teal-50 transition-colors"
            >
              <MessageSquare className="w-4 h-4 text-teal-600" />
              <span>Ask AI Health Assistant</span>
            </button>
            <button
              onClick={() => onNavigate('daily_tracking')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-teal-800/60 hover:bg-teal-800/80 text-white text-sm font-medium rounded-xl border border-white/20 transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Log Today's Vitals</span>
            </button>
          </div>
        </div>
      </div>

      {/* Quick Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Conditions */}
        <div 
          onClick={() => onNavigate('health_record')}
          className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm hover:border-teal-300 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Conditions</span>
            <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{loading ? '...' : activeConditionCount}</span>
            <span className="text-xs text-slate-500">recorded</span>
          </div>
          <p className="mt-2 text-xs text-slate-600 truncate">
            {conditions.length > 0 ? conditions.map(c => c.condition_name || c.description).slice(0, 2).join(', ') : 'No chronic conditions noted'}
          </p>
        </div>

        {/* Current Medications */}
        <div 
          onClick={() => onNavigate('health_record')}
          className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm hover:border-teal-300 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Prescriptions</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Pill className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{loading ? '...' : activeMedCount}</span>
            <span className="text-xs text-slate-500">active</span>
          </div>
          <p className="mt-2 text-xs text-slate-600 truncate">
            {medications.length > 0 ? medications.map(m => m.medication_name).slice(0, 2).join(', ') : 'No active medications'}
          </p>
        </div>

        {/* Allergies & Sensitivities */}
        <div 
          onClick={() => onNavigate('health_record')}
          className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm hover:border-teal-300 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Allergies</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{loading ? '...' : allergyCount}</span>
            <span className="text-xs text-slate-500">documented</span>
          </div>
          <p className="mt-2 text-xs text-slate-600 truncate">
            {allergies.length > 0 ? allergies.map(a => a.substance).join(', ') : 'No known drug or food allergies'}
          </p>
        </div>

        {/* Future Health Risk Insight */}
        <div 
          onClick={() => onNavigate('future_insights')}
          className="p-5 bg-gradient-to-br from-indigo-50/70 to-purple-50/70 rounded-xl border border-indigo-100 shadow-sm hover:border-indigo-300 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wider">12-Mo Disease Risk</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-900">Type 2 Diabetes</span>
          </div>
          <p className="mt-2 text-xs text-indigo-700 flex items-center gap-1 font-medium">
            <span>View longitudinal risk factors</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </p>
        </div>
      </div>

      {/* HMS Portals & Integrated Operations Stations */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 text-white shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              <Building2 className="w-4 h-4 text-teal-400" />
              <span>Aarogya-HMS Integrated Care Stations</span>
            </h2>
            <p className="text-xs text-slate-300">
              Role-synchronized 100-bed clinical operations, multi-agent AI event bus, and financial management
            </p>
          </div>
          <span className="text-[11px] font-mono text-teal-300 bg-teal-950/80 px-2.5 py-1 rounded-full border border-teal-800">
            Current User: {user?.role?.toUpperCase()}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Management Dashboard Card */}
          {(user?.role === 'admin' || user?.role === 'hospital_admin') && (
            <div 
              onClick={() => onNavigate('management')}
              className="p-4 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-teal-400/50 transition cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-teal-400">Management & BI</span>
                <Building2 className="w-4 h-4 text-teal-400" />
              </div>
              <p className="text-xs text-slate-300 mt-2">100-bed occupancy, conversational NL query BI, procurement alerts & revenue.</p>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-teal-300 group-hover:translate-x-0.5 transition-transform">
                <span>Open Management</span>
                <ArrowRight className="w-3 h-3" />
              </div>
            </div>
          )}

          {/* Doctor Portal Card */}
          {(user?.role === 'doctor' || user?.role === 'hospital_admin' || user?.role === 'admin') && (
            <div 
              onClick={() => onNavigate('doctor_portal')}
              className="p-4 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-indigo-400/50 transition cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-400">Doctor Station</span>
                <Stethoscope className="w-4 h-4 text-indigo-400" />
              </div>
              <p className="text-xs text-slate-300 mt-2">Pending patient EHR verification queue, consultation slots & clinical notes.</p>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-indigo-300 group-hover:translate-x-0.5 transition-transform">
                <span>Open Doctor Station</span>
                <ArrowRight className="w-3 h-3" />
              </div>
            </div>
          )}

          {/* Nurse Portal Card */}
          {(user?.role === 'nurse' || user?.role === 'hospital_admin' || user?.role === 'admin') && (
            <div 
              onClick={() => onNavigate('nurse_portal')}
              className="p-4 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-emerald-400/50 transition cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-emerald-400">Nurse Station</span>
                <HeartPulse className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-xs text-slate-300 mt-2">100-bed floor plan matrix, patient triage, bedside vitals recording & transfers.</p>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-emerald-300 group-hover:translate-x-0.5 transition-transform">
                <span>Open Nurse Station</span>
                <ArrowRight className="w-3 h-3" />
              </div>
            </div>
          )}

          {/* Billing & Invoices Card */}
          <div 
            onClick={() => onNavigate('billing')}
            className="p-4 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-amber-400/50 transition cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-400">Billing & RCM</span>
              <Receipt className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xs text-slate-300 mt-2">Invoices, assisted ICD-10 clinical coding, and payment settlements.</p>
            <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-amber-300 group-hover:translate-x-0.5 transition-transform">
              <span>View Invoices</span>
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>

          {/* Patient Longitudinal EHR Card */}
          <div 
            onClick={() => onNavigate('health_record')}
            className="p-4 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-purple-400/50 transition cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-purple-400">Patient EHR Export</span>
              <FileText className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-xs text-slate-300 mt-2">Longitudinal timeline, vitals trends & complete PDF clinical export.</p>
            <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-purple-300 group-hover:translate-x-0.5 transition-transform">
              <span>View Record</span>
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Latest Vitals & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Latest Vitals Card */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Latest Recorded Vitals</h2>
              <p className="text-xs text-slate-500">
                {latestLog ? `Recorded on ${latestLog.log_date} via ${latestLog.source}` : 'Historical baseline from medical record'}
              </p>
            </div>
            <button
              onClick={() => onNavigate('daily_tracking')}
              className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
            >
              <span>View 30-Day Trends</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
            {/* Blood Pressure */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Blood Pressure</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-xl font-extrabold text-slate-900">
                  {latestLog?.systolic_bp && latestLog?.diastolic_bp
                    ? `${latestLog.systolic_bp}/${latestLog.diastolic_bp}`
                    : '128/82'}
                </span>
                <span className="text-[10px] text-slate-500">mmHg</span>
              </div>
              <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
                Controlled
              </span>
            </div>

            {/* Fasting Glucose */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Fasting Glucose</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-xl font-extrabold text-slate-900">
                  {latestLog?.fasting_glucose ? latestLog.fasting_glucose : '108'}
                </span>
                <span className="text-[10px] text-slate-500">mg/dL</span>
              </div>
              <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700">
                Borderline
              </span>
            </div>

            {/* Pulse */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Heart Rate</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-xl font-extrabold text-slate-900">
                  {latestLog?.pulse ? latestLog.pulse : '74'}
                </span>
                <span className="text-[10px] text-slate-500">bpm</span>
              </div>
              <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
                Resting Normal
              </span>
            </div>

            {/* Oxygen Saturation */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">SpO2 Oxygen</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-xl font-extrabold text-slate-900">
                  {latestLog?.spo2 ? `${latestLog.spo2}%` : '98%'}
                </span>
              </div>
              <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
                Optimal
              </span>
            </div>
          </div>

          {/* Quick Check-in Prompt */}
          <div className="mt-6 p-4 rounded-xl bg-teal-50 border border-teal-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-teal-600 text-white flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">Daily Health Check-in</p>
                <p className="text-xs text-slate-600">Consistent tracking provides better longitudinal insights over time.</p>
              </div>
            </div>
            <button
              onClick={() => onNavigate('daily_tracking')}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors shrink-0"
            >
              Log Measurement
            </button>
          </div>
        </div>

        {/* Right Side: AI Assistant & Quick Actions */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center">
                <MessageSquare className="w-4 h-4" />
              </div>
              <h2 className="text-base font-bold text-slate-900">AI Health Assistant</h2>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Have questions about your lab results, new symptoms, or prescribed medications? Your assistant draws directly from verified medical guidelines.
            </p>

            <div className="mt-4 space-y-2">
              <div 
                onClick={() => onNavigate('assistant')}
                className="p-3 rounded-lg bg-slate-50 hover:bg-teal-50/70 border border-slate-200/70 text-xs text-slate-700 cursor-pointer transition flex items-center justify-between"
              >
                <span>"What does my fasting glucose score mean?"</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <div 
                onClick={() => onNavigate('assistant')}
                className="p-3 rounded-lg bg-slate-50 hover:bg-teal-50/70 border border-slate-200/70 text-xs text-slate-700 cursor-pointer transition flex items-center justify-between"
              >
                <span>"Check my symptoms before seeing a doctor"</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <div 
                onClick={() => onNavigate('health_record')}
                className="p-3 rounded-lg bg-slate-50 hover:bg-teal-50/70 border border-slate-200/70 text-xs text-slate-700 cursor-pointer transition flex items-center justify-between"
              >
                <span>"Upload and scan a new diagnostic report"</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={() => onNavigate('assistant')}
              className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Open Health Assistant</span>
            </button>
          </div>
        </div>
      </div>

      {/* Safety Notice Footer */}
      <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200/70 flex items-start gap-3 text-xs text-amber-900">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-bold">Medical Research & Educational Disclaimer:</span> Aarogya Drishti 2.0 provides patient self-management tools and AI-assisted educational summaries. It is not an FDA/CDSCO cleared medical diagnostic device. Always consult certified healthcare practitioners for clinical decisions. In an emergency, dial 112 or visit the nearest hospital emergency room.
        </div>
      </div>
    </div>
  );
};
