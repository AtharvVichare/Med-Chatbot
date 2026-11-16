import React, { useEffect, useState } from 'react';
import { 
  Sparkles, 
  RefreshCw,
  Heart,
  Activity,
  Flame,
  CheckCircle2,
  AlertTriangle,
  Stethoscope,
  Info,
  ShieldCheck,
  FileText,
  Users,
  Dna,
  Plus,
  Trash2,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { FutureRiskInsight, ConditionRiskEvaluation, FamilyMember } from '../types';

export const FutureInsightsPage: React.FC = () => {
  const { user } = useAuth();
  // Strictly display HIS (the logged-in patient's) and his family's health only
  const patientId = user?.patient_id || 'PAT-AARAV-001';

  const [insight, setInsight] = useState<FutureRiskInsight | null>(null);
  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // Navigation tabs: 'personal' (his health), 'family' (his family's health), or 'all'
  const [viewMode, setViewMode] = useState<'personal' | 'family'>('personal');
  const [domainFilter, setDomainFilter] = useState<string>('all');

  // Add Family Member Modal State
  const [showAddFamilyModal, setShowAddFamilyModal] = useState(false);
  const [relativeName, setRelativeName] = useState('');
  const [relationType, setRelationType] = useState('mother');
  const [lineage, setLineage] = useState<'maternal' | 'paternal' | ''>('maternal');
  const [isDeceased, setIsDeceased] = useState(false);
  const [conditionName, setConditionName] = useState('Type 2 Diabetes');
  const [ageAtOnset, setAgeAtOnset] = useState<number | ''>(50);
  const [notes, setNotes] = useState('');
  const [submittingFamily, setSubmittingFamily] = useState(false);

  const fetchPatientAndFamilyInsights = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [riskRes, familyRes] = await Promise.all([
        api.getFutureRisk(patientId),
        api.getPatientFamilyHistory(patientId)
      ]);
      setInsight(riskRes);
      setFamilyMembers(familyRes);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to retrieve prospective health insights');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatientAndFamilyInsights();
  }, [patientId]);

  const handleAddFamilyMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingFamily(true);
    try {
      const payload = {
        relative_name: relativeName.trim() || undefined,
        relation_type: relationType,
        lineage: lineage || undefined,
        is_deceased: isDeceased,
        notes: notes.trim() || undefined,
        conditions: conditionName.trim() ? [{
          condition_name: conditionName.trim(),
          approximate_age_at_onset: typeof ageAtOnset === 'number' ? ageAtOnset : undefined,
          notes: notes.trim() || undefined
        }] : []
      };

      await api.addPatientFamilyMember(patientId, payload);
      setShowAddFamilyModal(false);
      // Reset form
      setRelativeName('');
      setNotes('');
      // Refresh insights and family pedigree
      await fetchPatientAndFamilyInsights();
    } catch (err: any) {
      alert(`Failed to add family health record: ${err.message}`);
    } finally {
      setSubmittingFamily(false);
    }
  };

  const handleDeleteFamilyMember = async (memberId: string) => {
    if (!window.confirm('Remove this family member from your hereditary health pedigree?')) return;
    try {
      await api.deletePatientFamilyMember(patientId, memberId);
      await fetchPatientAndFamilyInsights();
    } catch (err: any) {
      alert(`Failed to remove family record: ${err.message}`);
    }
  };

  const getTierBadge = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'high':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'elevated':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'moderate':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'diagnosed':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'indeterminate':
        return 'bg-slate-100 text-slate-700 border-slate-300';
      case 'optimal':
      case 'low':
      default:
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'cardiovascular':
        return <Heart className="w-5 h-5 text-rose-600" />;
      case 'metabolic':
        return <Flame className="w-5 h-5 text-amber-600" />;
      case 'vascular':
        return <Activity className="w-5 h-5 text-indigo-600" />;
      case 'renal':
        return <Stethoscope className="w-5 h-5 text-teal-600" />;
      case 'respiratory':
        return <Activity className="w-5 h-5 text-sky-600" />;
      default:
        return <Sparkles className="w-5 h-5 text-indigo-600" />;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header - Displays Patient & Family Health Only */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Personal & Familial Health Insights</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Health Insights & Hereditary Disease Risk
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Verified longitudinal health observations and family pedigree analysis for{' '}
            <span className="font-semibold text-slate-800">{insight?.patient_name || user?.full_name || patientId}</span> ({patientId})
          </p>
        </div>

        {/* View Toggle & Actions */}
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-xl bg-slate-100 border border-slate-200/80 flex items-center">
            <button
              onClick={() => setViewMode('personal')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                viewMode === 'personal'
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>His Health Forecast</span>
            </button>
            <button
              onClick={() => setViewMode('family')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                viewMode === 'family'
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>Family Health Pedigree ({familyMembers.length})</span>
            </button>
          </div>

          <button
            onClick={fetchPatientAndFamilyInsights}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl shadow-xs transition disabled:opacity-50"
            title="Re-evaluate longitudinal risk"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Clinical Transparency Notice */}
      <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-200/80 text-xs text-indigo-950 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <p className="font-bold text-indigo-900">Patient & Family Health Context:</p>
          <p className="mt-0.5 text-indigo-800">
            This module evaluates the patient's individual electronic health record together with documented 1st and 2nd-degree family pedigree conditions. When baseline diagnostic laboratory panels are missing, the system refrains from fabricating chronic disease diagnoses and highlights recommended clinical screenings.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-16 text-center bg-white rounded-2xl border border-slate-200 text-xs text-slate-500 space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
          <p className="font-semibold text-slate-700 text-sm">Evaluating personal longitudinal EHR and family pedigree records...</p>
          <p className="text-slate-400">Extracting vitals, lab markers, and multi-generational hereditary predispositions.</p>
        </div>
      ) : errorMsg ? (
        <div className="p-6 bg-white rounded-2xl border border-rose-200 text-rose-800 text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <div>
            <p className="font-bold">Error Evaluating Health Insights</p>
            <p className="mt-1">{errorMsg}</p>
          </div>
        </div>
      ) : insight ? (
        <div className="space-y-6">

          {/* Integrated Family Hereditary Impact Banner (Always visible in both views) */}
          {insight.family_health_risk && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-purple-50 via-indigo-50 to-white border border-purple-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-purple-100 text-purple-700 mt-0.5">
                  <Dna className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold text-purple-700 uppercase tracking-wider">Hereditary Pedigree Analysis</span>
                    <span className="text-[10px] bg-purple-200/70 text-purple-900 font-bold px-2 py-0.5 rounded-full">
                      {insight.family_health_risk.total_relatives_tracked} Relatives Documented
                    </span>
                  </div>
                  <p className="text-xs text-slate-700 mt-1 font-medium">
                    {insight.family_health_risk.clinical_genetics_guidance}
                  </p>
                  {insight.family_health_risk.hereditary_predispositions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {insight.family_health_risk.hereditary_predispositions.map((pred, pIdx) => (
                        <span key={pIdx} className="text-[11px] bg-white border border-purple-200 text-purple-900 font-semibold px-2.5 py-0.5 rounded-md shadow-2xs">
                          • {pred}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={() => setViewMode(viewMode === 'personal' ? 'family' : 'personal')}
                className="self-start md:self-auto px-3.5 py-1.5 text-xs font-bold rounded-xl border border-purple-300 bg-white hover:bg-purple-50 text-purple-800 transition shrink-0"
              >
                {viewMode === 'personal' ? 'Manage Family Health' : 'Back to Personal Forecast'}
              </button>
            </div>
          )}

          {/* ============================================================== */}
          {/* VIEW MODE 1: HIS PERSONAL HEALTH RISK FORECAST                 */}
          {/* ============================================================== */}
          {viewMode === 'personal' && (
            <div className="space-y-6">
              {/* Data Completeness & Diagnostic Readiness Banner */}
              {insight.data_completeness && (
                <div className="p-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-2 rounded-xl ${
                        insight.data_completeness.readiness_level === 'COMPREHENSIVE'
                          ? 'bg-emerald-50 text-emerald-700'
                          : insight.data_completeness.readiness_level === 'PARTIAL_COVERAGE'
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        <Activity className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">EHR Diagnostic Data Completeness</h3>
                        <p className="text-xs text-slate-500">
                          Readiness Status: <span className="font-semibold text-slate-700">{insight.data_completeness.readiness_level.replace('_', ' ')}</span> ({insight.data_completeness.completeness_percentage}% biomarker coverage)
                        </p>
                      </div>
                    </div>

                    {/* Completeness Bar */}
                    <div className="w-full sm:w-48">
                      <div className="flex justify-between text-[11px] font-semibold text-slate-500 mb-1">
                        <span>Clinical Data Quality</span>
                        <span>{insight.data_completeness.completeness_percentage}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div 
                          className={`h-2 rounded-full transition-all duration-500 ${
                            insight.data_completeness.completeness_percentage >= 75
                              ? 'bg-emerald-500'
                              : insight.data_completeness.completeness_percentage >= 40
                              ? 'bg-amber-500'
                              : 'bg-rose-500'
                          }`}
                          style={{ width: `${insight.data_completeness.completeness_percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Biomarker Badges */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className={`p-2.5 rounded-xl border text-xs flex items-center gap-2 ${
                      insight.data_completeness.vitals_recorded 
                        ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' 
                        : 'bg-slate-50 border-slate-200 text-slate-500'
                    }`}>
                      <CheckCircle2 className={`w-4 h-4 shrink-0 ${insight.data_completeness.vitals_recorded ? 'text-emerald-600' : 'text-slate-400'}`} />
                      <div>
                        <span className="font-bold block text-[11px]">Serial Vitals</span>
                        <span className="text-[10px] opacity-80">{insight.data_completeness.vitals_recorded ? 'BP & SpO2 Tracked' : 'Not Recorded'}</span>
                      </div>
                    </div>

                    <div className={`p-2.5 rounded-xl border text-xs flex items-center gap-2 ${
                      insight.data_completeness.glycemic_panel_recorded 
                        ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' 
                        : 'bg-amber-50/60 border-amber-200 text-amber-900'
                    }`}>
                      {insight.data_completeness.glycemic_panel_recorded ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      ) : (
                        <Info className="w-4 h-4 text-amber-600 shrink-0" />
                      )}
                      <div>
                        <span className="font-bold block text-[11px]">Glycemic Panel</span>
                        <span className="text-[10px] opacity-80">
                          {insight.data_completeness.glycemic_panel_recorded ? 'Fasting Glucose & HbA1c' : 'Missing (Screening Needed)'}
                        </span>
                      </div>
                    </div>

                    <div className={`p-2.5 rounded-xl border text-xs flex items-center gap-2 ${
                      insight.data_completeness.lipid_panel_recorded 
                        ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' 
                        : 'bg-slate-50 border-slate-200 text-slate-500'
                    }`}>
                      <CheckCircle2 className={`w-4 h-4 shrink-0 ${insight.data_completeness.lipid_panel_recorded ? 'text-emerald-600' : 'text-slate-400'}`} />
                      <div>
                        <span className="font-bold block text-[11px]">Lipid Profile</span>
                        <span className="text-[10px] opacity-80">{insight.data_completeness.lipid_panel_recorded ? 'Chol / HDL / LDL' : 'Not Recorded'}</span>
                      </div>
                    </div>

                    <div className={`p-2.5 rounded-xl border text-xs flex items-center gap-2 ${
                      insight.data_completeness.renal_panel_recorded 
                        ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' 
                        : 'bg-slate-50 border-slate-200 text-slate-500'
                    }`}>
                      <CheckCircle2 className={`w-4 h-4 shrink-0 ${insight.data_completeness.renal_panel_recorded ? 'text-emerald-600' : 'text-slate-400'}`} />
                      <div>
                        <span className="font-bold block text-[11px]">Renal Markers</span>
                        <span className="text-[10px] opacity-80">{insight.data_completeness.renal_panel_recorded ? 'Microalbumin / Creatinine' : 'Not Recorded'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Missing Biomarkers Notice */}
                  {insight.data_completeness.missing_biomarkers.length > 0 && (
                    <div className="p-3 rounded-xl bg-amber-50/80 border border-amber-200/80 text-xs text-amber-900 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Transparent Biomarker Assessment: </span>
                        <span>
                          Missing {insight.data_completeness.missing_biomarkers.join(', ')}. Predictive models refrain from guessing disease onset for missing lab panels to protect against inaccurate disease labeling.
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Dynamic Primary Risk Hero Card */}
              <div className="p-6 bg-white rounded-2xl border border-slate-200/80 shadow-sm space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-4 border-b border-slate-100">
                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">
                      Primary Individual Health Risk Profile
                    </span>
                    <h2 className="text-2xl font-bold text-slate-900">{insight.target_condition}</h2>
                    <p className="text-xs text-slate-500">
                      Patient: <span className="font-semibold text-slate-700">{insight.patient_name || patientId}</span> ({insight.patient_age}y, {insight.patient_sex || 'Adult'}, {insight.is_smoker ? 'Smoker' : 'Non-smoker'}) · Lookback: <span className="font-semibold text-slate-700">{insight.lookback_window}</span> · Horizon: <span className="font-semibold text-slate-700">{insight.prediction_horizon}</span>
                    </p>
                  </div>

                  {/* Score & Tier Badge */}
                  <div className="text-left sm:text-right">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase block">12-Month Prospective Risk</span>
                    <div className="flex items-center sm:justify-end gap-2.5 mt-1">
                      <span className="text-3xl font-extrabold text-slate-900">
                        {insight.estimated_risk_score !== null && insight.estimated_risk_score !== undefined
                          ? `${(insight.estimated_risk_score * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getTierBadge(insight.risk_category || 'Low')}`}>
                        {insight.risk_category || 'Low'} Risk
                      </span>
                    </div>
                  </div>
                </div>

                {/* Primary Summary */}
                {insight.primary_risk_summary && (
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-700 leading-relaxed">
                    <div className="flex items-start gap-2.5">
                      <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                      <p>{insight.primary_risk_summary}</p>
                    </div>
                  </div>
                )}

                {/* Key Longitudinal Indicators Evaluated */}
                {insight.contributing_factors && insight.contributing_factors.length > 0 && (
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-3">Key Contributing Biomarkers & Clinical Indicators</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {insight.contributing_factors.map((factor, idx) => (
                        <div key={idx} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 space-y-1.5 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-800">{factor.factor}</span>
                            {factor.impact && (
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                                factor.impact === 'HIGH'
                                  ? 'bg-rose-100 text-rose-800'
                                  : factor.impact === 'ELEVATED'
                                  ? 'bg-amber-100 text-amber-800'
                                  : factor.impact === 'PRE_EXISTING'
                                  ? 'bg-purple-100 text-purple-800'
                                  : factor.impact === 'OPTIMAL'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-slate-200 text-slate-700'
                              }`}>
                                {factor.impact.replace('_', ' ')}
                              </span>
                            )}
                          </div>
                          {factor.metric && (
                            <p className="text-indigo-700 font-mono text-[11px] font-semibold">{factor.metric}</p>
                          )}
                          {factor.detail && (
                            <p className="text-[11px] text-slate-500 leading-normal">{factor.detail}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Multi-Condition Prospective Disease Risk Matrix */}
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">Multi-System Chronic Disease Risk Matrix</h3>
                    <p className="text-xs text-slate-500">
                      Comprehensive 12-month prospective risk forecasting across 5 clinical disease domains
                    </p>
                  </div>

                  {/* Domain Filter Pills */}
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                    {['all', 'cardiovascular', 'metabolic', 'vascular', 'renal', 'respiratory'].map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setDomainFilter(tab)}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition ${
                          domainFilter === tab
                            ? 'bg-indigo-600 text-white shadow-xs'
                            : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(insight.condition_evaluations || [])
                    .filter((c) => domainFilter === 'all' || c.category.toLowerCase() === domainFilter)
                    .map((cond: ConditionRiskEvaluation, idx: number) => {
                      const isPreExisting = cond.status === 'PRE_EXISTING_CONDITION';
                      const isMissingLabs = cond.status === 'INSUFFICIENT_BIOMARKERS';

                      return (
                        <div 
                          key={idx} 
                          className="p-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-4 flex flex-col justify-between"
                        >
                          <div>
                            {/* Card Header */}
                            <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-100">
                              <div className="flex items-start gap-2.5">
                                <div className="p-2 rounded-xl bg-slate-50 border border-slate-200/60 mt-0.5">
                                  {getCategoryIcon(cond.category)}
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                      {cond.category} · ICD-10: {cond.icd10_code}
                                    </span>
                                  </div>
                                  <h4 className="text-base font-bold text-slate-900 mt-0.5">{cond.condition_name}</h4>
                                </div>
                              </div>

                              {/* Tier Badge */}
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border shrink-0 ${getTierBadge(cond.risk_tier)}`}>
                                {cond.risk_tier}
                              </span>
                            </div>

                            {/* Risk Progress Bar */}
                            <div className="mt-4">
                              <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
                                <span className="text-slate-500">
                                  {isPreExisting ? 'Clinical Diagnosis Status' : isMissingLabs ? 'Biomarker Status' : 'Estimated 12-Mo Incident Risk'}
                                </span>
                                <span className="text-slate-900 font-bold">
                                  {isPreExisting 
                                    ? 'Documented in EHR' 
                                    : isMissingLabs 
                                    ? 'Baseline Labs Missing' 
                                    : cond.risk_score !== null && cond.risk_score !== undefined 
                                    ? `${(cond.risk_score * 100).toFixed(1)}%` 
                                    : '—'}
                                </span>
                              </div>
                              
                              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                                <div 
                                  className={`h-2 rounded-full transition-all duration-500 ${
                                    isPreExisting 
                                      ? 'bg-purple-600' 
                                      : isMissingLabs 
                                      ? 'bg-slate-300' 
                                      : (cond.risk_score || 0) >= 0.5 
                                      ? 'bg-rose-500' 
                                      : (cond.risk_score || 0) >= 0.25 
                                      ? 'bg-amber-500' 
                                      : 'bg-emerald-500'
                                  }`}
                                  style={{ width: `${isPreExisting ? 100 : isMissingLabs ? 0 : Math.min(100, (cond.risk_score || 0) * 100)}%` }}
                                />
                              </div>
                            </div>

                            {/* Contributing Factors */}
                            {cond.contributing_factors.length > 0 && (
                              <div className="mt-3.5 space-y-2">
                                <span className="text-[11px] font-bold text-slate-600 block">Evaluated Clinical Factors:</span>
                                <div className="space-y-1.5">
                                  {cond.contributing_factors.map((f, fIdx) => (
                                    <div key={fIdx} className="text-xs p-2 rounded-lg bg-slate-50 border border-slate-200/60 flex items-start justify-between gap-2">
                                      <div>
                                        <span className="font-semibold text-slate-800">{f.factor}: </span>
                                        <span className="text-slate-500 text-[11px]">{f.detail}</span>
                                      </div>
                                      {f.metric && (
                                        <span className="font-mono text-[11px] font-bold text-indigo-700 shrink-0">{f.metric}</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Clinical Recommendations */}
                          {cond.clinical_recommendations && cond.clinical_recommendations.length > 0 && (
                            <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
                              <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
                                <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                                Evidence-Based Clinical Prevention Guidance:
                              </span>
                              <ul className="space-y-1 text-slate-600 text-[11px] list-disc list-inside">
                                {cond.clinical_recommendations.map((rec, rIdx) => (
                                  <li key={rIdx}>{rec}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Longitudinal Biomarker Measurements Audit Panel */}
              <div className="p-6 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">Verified Longitudinal Biomarker Measurements</h3>
                  </div>
                  <span className="text-xs text-slate-400">Strictly observed EHR values (Zero synthetic fallbacks)</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Mean Systolic BP</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.mean_systolic_bp 
                        ? `${insight.historical_metrics_analyzed.mean_systolic_bp} mmHg` 
                        : 'Not Recorded'}
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Mean Diastolic BP</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.mean_diastolic_bp 
                        ? `${insight.historical_metrics_analyzed.mean_diastolic_bp} mmHg` 
                        : 'Not Recorded'}
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Fasting Glucose</span>
                    <p className={`font-semibold text-sm mt-0.5 ${
                      insight.historical_metrics_analyzed.latest_fasting_glucose_mg_dl
                        ? 'text-slate-900'
                        : 'text-amber-700 text-xs'
                    }`}>
                      {insight.historical_metrics_analyzed.latest_fasting_glucose_mg_dl 
                        ? `${insight.historical_metrics_analyzed.latest_fasting_glucose_mg_dl} mg/dL` 
                        : 'Not Tested in EHR'}
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Glycated HbA1c</span>
                    <p className={`font-semibold text-sm mt-0.5 ${
                      insight.historical_metrics_analyzed.latest_hba1c_pct
                        ? 'text-slate-900'
                        : 'text-amber-700 text-xs'
                    }`}>
                      {insight.historical_metrics_analyzed.latest_hba1c_pct 
                        ? `${insight.historical_metrics_analyzed.latest_hba1c_pct}%` 
                        : 'Not Tested in EHR'}
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Mean SpO2 Saturation</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.mean_spo2_pct 
                        ? `${insight.historical_metrics_analyzed.mean_spo2_pct}%` 
                        : 'Not Recorded'}
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Smoker Status</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.is_smoker ? 'Active Smoker' : 'Non-Smoker'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* VIEW MODE 2: HIS FAMILY HEALTH & HEREDITARY PEDIGREE           */}
          {/* ============================================================== */}
          {viewMode === 'family' && (
            <div className="space-y-6">
              {/* Family Pedigree Header & Add Button */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Documented Family Members & Hereditary Health</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Multi-generational hereditary health history for 1st and 2nd-degree relatives of {insight.patient_name || patientId}
                  </p>
                </div>

                <button
                  onClick={() => setShowAddFamilyModal(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Family Member</span>
                </button>
              </div>

              {/* Family Members Grid */}
              {familyMembers.length === 0 ? (
                <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 space-y-3">
                  <Users className="w-10 h-10 text-slate-300 mx-auto" />
                  <h4 className="text-sm font-bold text-slate-700">No Family Health Records Documented</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    Documenting your parents, siblings, and grandparents provides essential clinical insight into hereditary genetic predispositions for cardiovascular disease, diabetes, and hypertension.
                  </p>
                  <button
                    onClick={() => setShowAddFamilyModal(true)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold shadow-xs"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add First Family Member</span>
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {familyMembers.map((member) => {
                    const isFirstDegree = ['mother', 'father', 'brother', 'sister', 'son', 'daughter'].includes(member.relation_type.toLowerCase());

                    return (
                      <div 
                        key={member.id} 
                        className="p-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-4 flex flex-col justify-between"
                      >
                        <div>
                          {/* Member Header */}
                          <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-100">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider capitalize">
                                  {member.relation_type.replace('_', ' ')}
                                </span>
                                {member.lineage && (
                                  <span className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded capitalize">
                                    {member.lineage}
                                  </span>
                                )}
                              </div>
                              <h4 className="text-base font-bold text-slate-900 mt-1">
                                {member.relative_name || `Family ${member.relation_type}`}
                              </h4>
                            </div>

                            <button
                              onClick={() => handleDeleteFamilyMember(member.id)}
                              className="text-slate-400 hover:text-rose-600 p-1 rounded transition"
                              title="Delete family member"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>

                          {/* Status & Degree Badge */}
                          <div className="flex items-center gap-2 mt-3">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              isFirstDegree ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100 text-slate-700'
                            }`}>
                              {isFirstDegree ? '1st-Degree Relative' : '2nd-Degree Relative'}
                            </span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              member.is_deceased ? 'bg-slate-200 text-slate-800' : 'bg-emerald-100 text-emerald-800'
                            }`}>
                              {member.is_deceased ? 'Deceased' : 'Living'}
                            </span>
                          </div>

                          {/* Member Documented Conditions */}
                          <div className="mt-4 space-y-2">
                            <span className="text-[11px] font-bold text-slate-600 block">Documented Conditions:</span>
                            {member.conditions && member.conditions.length > 0 ? (
                              <div className="space-y-1.5">
                                {member.conditions.map((cond, cIdx) => (
                                  <div key={cIdx} className="text-xs p-2.5 rounded-xl bg-purple-50/70 border border-purple-200/70 space-y-0.5">
                                    <div className="flex items-center justify-between">
                                      <span className="font-bold text-purple-950">{cond.condition_name}</span>
                                      {cond.approximate_age_at_onset && (
                                        <span className="text-[10px] text-purple-800 font-semibold">
                                          Onset: {cond.approximate_age_at_onset}y
                                        </span>
                                      )}
                                    </div>
                                    {cond.notes && (
                                      <p className="text-[11px] text-purple-800/80">{cond.notes}</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs text-slate-400 italic">No chronic medical conditions documented.</p>
                            )}
                          </div>

                          {/* Member Notes */}
                          {member.notes && (
                            <div className="mt-3 text-[11px] text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-200/60">
                              <span className="font-semibold text-slate-700">Notes: </span>
                              <span>{member.notes}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

        </div>
      ) : null}

      {/* ============================================================== */}
      {/* ADD FAMILY MEMBER MODAL DIALOG                                  */}
      {/* ============================================================== */}
      {showAddFamilyModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Add Family Health Pedigree Record</h3>
              </div>
              <button 
                onClick={() => setShowAddFamilyModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddFamilyMember} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Relative Name</label>
                <input
                  type="text"
                  placeholder="e.g. Savitri Nair"
                  value={relativeName}
                  onChange={(e) => setRelativeName(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Relationship Type *</label>
                  <select
                    value={relationType}
                    onChange={(e) => setRelationType(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
                  >
                    <option value="mother">Mother (1st-Degree)</option>
                    <option value="father">Father (1st-Degree)</option>
                    <option value="sister">Sister (1st-Degree)</option>
                    <option value="brother">Brother (1st-Degree)</option>
                    <option value="grandmother_maternal">Maternal Grandmother</option>
                    <option value="grandfather_maternal">Maternal Grandfather</option>
                    <option value="grandmother_paternal">Paternal Grandmother</option>
                    <option value="grandfather_paternal">Paternal Grandfather</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Lineage</label>
                  <select
                    value={lineage}
                    onChange={(e) => setLineage(e.target.value as any)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
                  >
                    <option value="">None / Sibling</option>
                    <option value="maternal">Maternal (Mother's side)</option>
                    <option value="paternal">Paternal (Father's side)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="deceasedCheck"
                  checked={isDeceased}
                  onChange={(e) => setIsDeceased(e.target.checked)}
                  className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                />
                <label htmlFor="deceasedCheck" className="text-xs font-semibold text-slate-700">
                  Relative is deceased
                </label>
              </div>

              <div className="pt-2 border-t border-slate-100 space-y-3">
                <span className="text-xs font-bold text-slate-800 block">Diagnosed Hereditary Medical Condition</span>
                
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-[11px] font-semibold text-slate-600 mb-1">Condition Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Type 2 Diabetes, Hypertension, Coronary Artery Disease"
                      value={conditionName}
                      onChange={(e) => setConditionName(e.target.value)}
                      className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-600 mb-1">Onset Age</label>
                    <input
                      type="number"
                      placeholder="e.g. 52"
                      value={ageAtOnset}
                      onChange={(e) => setAgeAtOnset(e.target.value ? parseInt(e.target.value) : '')}
                      className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">Clinical Notes</label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Managed with metformin, no diabetic complications reported."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddFamilyModal(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingFamily}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs disabled:opacity-50"
                >
                  {submittingFamily ? 'Saving...' : 'Add to Pedigree'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
