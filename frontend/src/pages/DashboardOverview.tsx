import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Calendar, 
  Activity, 
  Stethoscope, 
  ArrowUpRight, 
  ShieldCheck, 
  AlertTriangle 
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const DashboardOverview: React.FC<{ onNavigate: (tab: string) => void }> = ({ onNavigate }) => {
  const { user } = useAuth();
  const [patientCount, setPatientCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        if (user?.role !== 'public_health_analyst' && user?.role !== 'patient') {
          const res = await api.getPatients(1, 1);
          setPatientCount(res.total);
        }
      } catch (err) {
        console.error('Failed to load patient summary count:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, [user]);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-teal-900 via-slate-900 to-indigo-950 text-white shadow-lg">
        <div className="max-w-2xl">
          <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-teal-500/20 text-teal-300 border border-teal-500/30 mb-3">
            Clinical AI Workspace
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Welcome, {user?.full_name}
          </h2>
          <p className="text-slate-300 text-sm mt-2 leading-relaxed">
            Aarogya Drishti 2.0 provides longitudinal clinical record navigation, evidence-grounded 
            guideline retrieval, and experimental differential symptom analysis for clinical research.
          </p>
          <div className="flex flex-wrap gap-3 mt-5">
            <button
              onClick={() => onNavigate('prediction')}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold rounded-xl shadow-md transition-colors flex items-center gap-1.5"
            >
              <Stethoscope className="w-3.5 h-3.5" />
              <span>Launch Symptom Analysis</span>
            </button>
            <button
              onClick={() => onNavigate('knowledge')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
            >
              Explore Medical References
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Cohort Patients</span>
            <Users className="w-4 h-4 text-teal-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900">
            {loading ? '...' : patientCount !== null ? patientCount.toLocaleString() : '1,000'}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Synthetic longitudinal cohort</p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Clinical Encounters</span>
            <Calendar className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900">3,612</p>
          <p className="text-[11px] text-slate-500 mt-1">Inpatient & OPD encounters</p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Observations</span>
            <Activity className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900">14,264</p>
          <p className="text-[11px] text-slate-500 mt-1">Biomarkers & vital signs</p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Reference Vectors</span>
            <ShieldCheck className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900">57 v2 Chunks</p>
          <p className="text-[11px] text-slate-500 mt-1">WHO & MedlinePlus guidelines</p>
        </div>
      </div>

      {/* Highlights / Quick Access Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Stethoscope className="w-4 h-4 text-teal-600" />
            <span>AI Symptom Differential Engine</span>
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Submit observed clinical symptoms to our server-enforced Logistic Regression classifier 
            to calculate experimental differential rankings across 41 disease categories, with 
            grounded explanations synthesized directly from official clinical references.
          </p>
          <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-100 flex items-center justify-between">
            <span className="text-xs font-medium text-teal-900">
              Zero client tampering • 132 validated symptom features
            </span>
            <button
              onClick={() => onNavigate('prediction')}
              className="text-xs font-semibold text-teal-700 hover:text-teal-900 inline-flex items-center gap-1"
            >
              Analyze <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Safety Guardrails & Regulatory Boundaries</span>
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Aarogya Drishti 2.0 enforces a strict research quarantine. Symptom features and 
            patient longitudinal records are never exposed to public LLMs or external indexes. 
            All differential outputs are experimental decision-support tools, not diagnostic devices.
          </p>
          <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/60 text-xs text-amber-900">
            National Emergency Guidance: In cases of severe acute distress, immediately dial <strong>112</strong> or <strong>108</strong> (Ambulance).
          </div>
        </div>
      </div>
    </div>
  );
};

