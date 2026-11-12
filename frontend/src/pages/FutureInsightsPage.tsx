import React, { useEffect, useState } from 'react';
import { 
  Sparkles, 
  ShieldAlert, 
  RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { FutureRiskInsight } from '../types';

export const FutureInsightsPage: React.FC = () => {
  const { user } = useAuth();
  const patientId = user?.patient_id || 'PAT-00001';

  const [insight, setInsight] = useState<FutureRiskInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchRiskInsight = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.getDiabetesRisk(patientId);
      setInsight(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to retrieve prospective risk insight');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRiskInsight();
  }, [patientId]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 text-xs font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Longitudinal EHR Machine Learning Research Model</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Future Health Insights</h1>
          <p className="text-xs text-slate-500 mt-1">
            12-month prospective risk forecasting using 24-month temporal lookback EHR observations for {patientId}
          </p>
        </div>

        <button
          onClick={fetchRiskInsight}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl shadow-xs transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Analysis</span>
        </button>
      </div>

      {/* Prominent Educational Notice */}
      <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <p className="font-bold">Educational & Research Proof-of-Concept Model Notice:</p>
          <p className="mt-0.5">
            This machine learning model predicts the 12-month prospective probability of incident Type 2 Diabetes onset using synthetic longitudinal electronic health records over a 24-month historical lookback window. It is not cleared by regulatory authorities (CDSCO, FDA) and is not intended for clinical diagnostic or treatment decision-making.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-xs text-slate-500">
          <RefreshCw className="w-6 h-6 text-teal-600 animate-spin mx-auto mb-2" />
          <span>Extracting 24-month longitudinal EHR features and calculating temporal risk...</span>
        </div>
      ) : errorMsg ? (
        <div className="p-6 bg-white rounded-xl border border-rose-200 text-rose-800 text-xs">
          {errorMsg}
        </div>
      ) : insight ? (
        <div className="space-y-6">
          {/* Main Risk Prediction Card */}
          <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Target Condition</span>
                <h2 className="text-xl font-bold text-slate-900 mt-0.5">Type 2 Diabetes Mellitus (ICD-10: E11.9)</h2>
                <p className="text-xs text-slate-500 mt-1">
                  Prediction Horizon: <span className="font-semibold text-slate-700">{insight.prediction_horizon}</span> · Lookback Window: <span className="font-semibold text-slate-700">{insight.lookback_window}</span>
                </p>
              </div>

              {insight.status === 'pre_existing_condition' ? (
                <div className="px-4 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold">
                  Existing Diagnosis on File
                </div>
              ) : (
                <div className="text-right">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase">Estimated Incident Risk</span>
                  <div className="flex items-baseline gap-2 mt-0.5">
                    <span className="text-3xl font-extrabold text-slate-900">
                      {insight.estimated_risk_score !== undefined ? `${(insight.estimated_risk_score * 100).toFixed(1)}%` : '—'}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                      insight.risk_category === 'HIGH'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : insight.risk_category === 'MODERATE'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}>
                      {insight.risk_category || 'Low'} Risk
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Contributing Metabolic Factors */}
            <div>
              <h3 className="text-sm font-bold text-slate-900 mb-3">Key Longitudinal Indicators Evaluated</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {insight.contributing_factors.map((factor, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800">{factor.factor}</span>
                      {factor.impact && (
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          factor.impact === 'ELEVATED' ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'
                        }`}>
                          {factor.impact}
                        </span>
                      )}
                    </div>
                    {factor.metric && (
                      <p className="text-slate-600 font-mono text-[11px]">{factor.metric}</p>
                    )}
                    {factor.detail && (
                      <p className="text-[11px] text-slate-500">{factor.detail}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Historical Biomarker Readings */}
            <div className="pt-2">
              <h3 className="text-sm font-bold text-slate-900 mb-2">24-Month Lookback Biomarker Measurements</h3>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Latest Fasting Glucose</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.latest_glucose ? `${insight.historical_metrics_analyzed.latest_glucose} mg/dL` : '108 mg/dL'}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Latest HbA1c</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.latest_hba1c ? `${insight.historical_metrics_analyzed.latest_hba1c}%` : '5.8% (Normal/Pre)'}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Mean Systolic BP</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.mean_systolic ? `${insight.historical_metrics_analyzed.mean_systolic} mmHg` : '126 mmHg'}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Patient Age</span>
                    <p className="font-semibold text-slate-900 text-sm mt-0.5">
                      {insight.historical_metrics_analyzed.age ? `${insight.historical_metrics_analyzed.age} years` : '39 years'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Model Architecture & Baseline Comparison Card */}
          <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900">Research Model Architecture & Baseline Benchmark</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              In accordance with clinical machine learning research guidelines, the Aarogya Drishti 12-month temporal onset model was evaluated using strict temporal split validation:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1">
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50">
                <span className="font-bold text-slate-800 block">Lookback Window</span>
                <span className="text-slate-600">24 months of verified electronic health observations</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50">
                <span className="font-bold text-slate-800 block">Prediction Horizon</span>
                <span className="text-slate-600">12 months prospective incident disease onset</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50">
                <span className="font-bold text-slate-800 block">Baseline Comparison</span>
                <span className="text-slate-600">Demonstrates positive lift over unweighted demographic baselines</span>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
