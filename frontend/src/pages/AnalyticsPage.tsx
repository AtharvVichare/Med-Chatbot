import React from 'react';
import { BarChart3, TrendingUp, PieChart, ShieldCheck } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-600" />
          <span>Public Health Epidemiology & Cohort Analytics</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          De-identified population statistics, disease frequency distributions, and epidemiological monitoring.
        </p>
      </div>

      <div className="p-4 rounded-xl bg-purple-50/70 border border-purple-200/60 text-purple-900 text-xs flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-purple-700 mt-0.5 shrink-0" />
        <p className="leading-relaxed">
          <strong>Privacy Compliance Notice:</strong> Identifiable patient details, names, and contact information 
          are mathematically masked. Aggregated cohort statistics reflect synthetic epidemiological surveillance.
        </p>
      </div>

      {/* Cohort Overview Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Total Monitored Cohort
          </span>
          <p className="text-2xl font-bold text-slate-900">1,000</p>
          <span className="text-[11px] text-emerald-600 font-medium">100% anonymized longitudinal records</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Top Prevalent Condition
          </span>
          <p className="text-2xl font-bold text-slate-900">Essential Hypertension</p>
          <span className="text-[11px] text-indigo-600 font-medium">ICD-10 I10 • 38.4% prevalence</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Cardiovascular Risk (High/Very High)
          </span>
          <p className="text-2xl font-bold text-slate-900">18.2%</p>
          <span className="text-[11px] text-amber-600 font-medium">WHO SEAR D model stratified</span>
        </div>
      </div>

      {/* Distribution Graphs & Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <PieChart className="w-4 h-4 text-purple-600" />
            <span>Disease Prevalence in Synthetic Registry</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div>
              <div className="flex justify-between mb-1">
                <span className="font-medium text-slate-700">Essential Hypertension (I10)</span>
                <span className="font-bold text-slate-900">384 cases</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div className="bg-purple-600 h-2 rounded-full" style={{ width: '38.4%' }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="font-medium text-slate-700">Type 2 Diabetes Mellitus (E11)</span>
                <span className="font-bold text-slate-900">296 cases</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div className="bg-teal-600 h-2 rounded-full" style={{ width: '29.6%' }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="font-medium text-slate-700">Bronchial Asthma (J45)</span>
                <span className="font-bold text-slate-900">182 cases</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div className="bg-indigo-600 h-2 rounded-full" style={{ width: '18.2%' }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="font-medium text-slate-700">Chronic Kidney Disease (N18)</span>
                <span className="font-bold text-slate-900">94 cases</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div className="bg-amber-600 h-2 rounded-full" style={{ width: '9.4%' }}></div>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-teal-600" />
            <span>Surveillance Encounters by Month</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl flex justify-between items-center">
              <span className="font-medium text-slate-700">October 2026</span>
              <span className="font-bold text-teal-700">412 visits</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl flex justify-between items-center">
              <span className="font-medium text-slate-700">September 2026</span>
              <span className="font-bold text-teal-700">388 visits</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl flex justify-between items-center">
              <span className="font-medium text-slate-700">August 2026</span>
              <span className="font-bold text-teal-700">355 visits</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl flex justify-between items-center">
              <span className="font-medium text-slate-700">July 2026</span>
              <span className="font-bold text-teal-700">321 visits</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
