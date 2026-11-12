import React, { useState, useEffect } from 'react';
import {
  Stethoscope,
  Search,
  X,
  AlertCircle,
  CheckCircle2,
  BookOpen,
  Clock,
  ShieldAlert,
  Info,
  ExternalLink,
  Flame,
  Wind,
  HeartCrack,
  Activity,
  AlertTriangle,
  PhoneCall
} from 'lucide-react';
import { api } from '../services/api';
import type { PredictAndExplainResponse, SymptomPredictResponse, SafetyWarning } from '../types';

export const SymptomAnalysisPage: React.FC = () => {
  const [allSymptoms, setAllSymptoms] = useState<string[]>([]);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoadingSymptoms, setIsLoadingSymptoms] = useState(true);

  // Quality & Contextual Assessment Fields
  const [duration, setDuration] = useState<string>('1-3 days');
  const [severity, setSeverity] = useState<string>('mild');
  const [progression, setProgression] = useState<string>('stable');
  const [hasFever, setHasFever] = useState<boolean>(false);
  const [breathingDifficulty, setBreathingDifficulty] = useState<boolean>(false);
  const [chestDiscomfort, setChestDiscomfort] = useState<boolean>(false);
  const [includeGeminiExplanation, setIncludeGeminiExplanation] = useState<boolean>(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [predictResult, setPredictResult] = useState<SymptomPredictResponse | null>(null);
  const [explainResult, setExplainResult] = useState<PredictAndExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSymptoms = async () => {
      try {
        const symptoms = await api.getSymptomsList();
        setAllSymptoms(symptoms);
      } catch (err: any) {
        setError('Failed to fetch symptom vocabulary from backend.');
      } finally {
        setIsLoadingSymptoms(false);
      }
    };
    fetchSymptoms();
  }, []);

  const toggleSymptom = (symptom: string) => {
    if (selectedSymptoms.includes(symptom)) {
      setSelectedSymptoms(selectedSymptoms.filter(s => s !== symptom));
    } else {
      setSelectedSymptoms([...selectedSymptoms, symptom]);
    }
  };

  const removeSymptom = (symptom: string) => {
    setSelectedSymptoms(selectedSymptoms.filter(s => s !== symptom));
  };

  const filteredSymptoms = allSymptoms.filter(s =>
    s.toLowerCase().replace(/_/g, ' ').includes(searchQuery.toLowerCase().trim()) &&
    !selectedSymptoms.includes(s)
  );

  const handleSubmit = async () => {
    if (selectedSymptoms.length === 0) {
      setError('Please select at least one symptom.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setPredictResult(null);
    setExplainResult(null);

    const payload = {
      symptoms: selectedSymptoms,
      duration,
      severity,
      progression,
      has_fever: hasFever,
      breathing_difficulty: breathingDifficulty,
      chest_discomfort: chestDiscomfort
    };

    try {
      if (includeGeminiExplanation) {
        const response = await api.predictAndExplain(payload);
        setExplainResult(response);
      } else {
        const response = await api.predictOnly(payload);
        setPredictResult(response);
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed. Please verify connection to backend server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetSelection = () => {
    setSelectedSymptoms([]);
    setPredictResult(null);
    setExplainResult(null);
    setError(null);
    setHasFever(false);
    setBreathingDifficulty(false);
    setChestDiscomfort(false);
  };

  // Harmonize displayed output between predictOnly and predictAndExplain
  const activePredictions = explainResult?.original_predictions || predictResult?.predictions || [];
  const safetyWarnings: SafetyWarning[] = explainResult?.safety_warnings || predictResult?.safety_warnings || [];
  const evidenceStatus = explainResult?.evidence_status || predictResult?.evidence_status || 'UNKNOWN';
  const abstentionReason = predictResult?.abstention_reason;
  const isAbstained = (evidenceStatus === 'INSUFFICIENT_INFORMATION' || (activePredictions.length === 0 && !isSubmitting));

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Stethoscope className="w-5 h-5 text-teal-600" />
          <span>Symptom Evaluation & Clinical Safety Triage</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Evidence-calibrated statistical evaluation with independent deterministic safety screening and optional grounded reference synthesis.
        </p>
      </div>

      {/* Disclaimers & Privacy Notice */}
      <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200/80 text-amber-900 text-xs space-y-1.5">
        <div className="flex items-center gap-2 font-semibold">
          <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0" />
          <span>Clinical Proof-of-Concept & Non-Diagnostic Advisory:</span>
        </div>
        <p className="leading-relaxed">
          This system provides <strong>experimental statistical model predictions</strong> based on research data (304 unique patterns). Model scores reflect uncalibrated statistical similarities, <strong>not confirmed clinical probabilities or medical diagnoses</strong>.
          When external clinical explanation is enabled, only predicted disease category titles are processed via Google Gemini to summarize public medical guidelines.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Symptom Picker & Quality Assessment (5 cols) */}
          <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">1. Symptom Selection</h3>
              <span className="text-[11px] font-semibold text-slate-400">
                {allSymptoms.length} standardized features
              </span>
            </div>

            {/* Search Box */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search symptoms (e.g. fever, cough, chest)..."
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              />
            </div>

            {/* Selected Symptom Chips */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-700">
                  Selected ({selectedSymptoms.length})
                </span>
                {selectedSymptoms.length > 0 && (
                  <button
                    onClick={resetSelection}
                    className="text-[11px] font-medium text-rose-600 hover:text-rose-700"
                  >
                    Clear all
                  </button>
                )}
              </div>

              {selectedSymptoms.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-2">
                  No symptoms selected yet. Pick from list below.
                </p>
              ) : (
                <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-2 bg-slate-50 rounded-xl border border-slate-200/60">
                  {selectedSymptoms.map(sym => (
                    <span
                      key={sym}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-teal-100 text-teal-800 border border-teal-200"
                    >
                      <span>{sym.replace(/_/g, ' ')}</span>
                      <button
                        onClick={() => removeSymptom(sym)}
                        className="hover:text-teal-950 focus:outline-none"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Available Symptoms List */}
            <div>
              <span className="text-xs font-semibold text-slate-700 block mb-2">
                Available Symptoms
              </span>
              {isLoadingSymptoms ? (
                <div className="text-center py-6 text-xs text-slate-400">Loading symptom vocabulary...</div>
              ) : (
                  <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
                    {filteredSymptoms.length === 0 ? (
                      <p className="text-xs text-slate-400 py-3 text-center">No matching symptoms found</p>
                    ) : (
                      filteredSymptoms.map(sym => (
                        <button
                          key={sym}
                          onClick={() => toggleSymptom(sym)}
                          className="w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-slate-100 text-slate-700 flex items-center justify-between transition-colors"
                        >
                          <span>{sym.replace(/_/g, ' ')}</span>
                          <span className="text-teal-600 font-bold text-sm">+</span>
                        </button>
                      ))
                    )}
                  </div>
            )}
                </div>

          {/* Section 2: Clinical Quality & Severity Assessment */}
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-indigo-600" />
                  <span>2. Symptom Quality & Red Flag Screening</span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  Evaluated by independent clinical safety rules; does not alter ML feature vector.
                </p>

                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[11px] font-medium text-slate-600 block mb-1">Duration</label>
                    <select
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-full p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
                    >
                      <option value="< 24 hours">&lt; 24 hours</option>
                      <option value="1-3 days">1-3 days</option>
                      <option value="4-7 days">4-7 days</option>
                      <option value="> 1 week">&gt; 1 week</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] font-medium text-slate-600 block mb-1">Severity</label>
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                      className="w-full p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
                    >
                      <option value="mild">Mild</option>
                      <option value="moderate">Moderate</option>
                      <option value="severe">Severe</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] font-medium text-slate-600 block mb-1">Progression</label>
                    <select
                      value={progression}
                      onChange={(e) => setProgression(e.target.value)}
                      className="w-full p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700"
                    >
                      <option value="improving">Improving</option>
                      <option value="stable">Stable</option>
                      <option value="worsening">Worsening</option>
                    </select>
                  </div>
                </div>

                {/* Checkbox Red Flags */}
                <div className="space-y-2 pt-1 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                    <input
                      type="checkbox"
                      checked={hasFever}
                      onChange={(e) => setHasFever(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                    <Flame className="w-3.5 h-3.5 text-amber-500" />
                    <span>Elevated body temperature / fever</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                    <input
                      type="checkbox"
                      checked={breathingDifficulty}
                      onChange={(e) => setBreathingDifficulty(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                    <Wind className="w-3.5 h-3.5 text-sky-500" />
                    <span>Shortness of breath / breathing difficulty</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                    <input
                      type="checkbox"
                      checked={chestDiscomfort}
                      onChange={(e) => setChestDiscomfort(e.target.checked)}
                      className="rounded text-teal-600 focus:ring-teal-500"
                    />
                    <HeartCrack className="w-3.5 h-3.5 text-rose-500" />
                    <span>Chest discomfort, tightness, or pain</span>
                  </label>
                </div>
              </div>

              {/* Section 3: Privacy & Gemini Toggling */}
              <div className="pt-3 border-t border-slate-100">
                <label className="flex items-start gap-2 cursor-pointer text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={includeGeminiExplanation}
                    onChange={(e) => setIncludeGeminiExplanation(e.target.checked)}
                    className="mt-0.5 rounded text-teal-600 focus:ring-teal-500"
                  />
                  <div>
                    <span className="font-semibold block text-slate-900">Include Grounded Gemini Reference Explanation</span>
                    <span className="text-[11px] text-slate-400 block leading-tight">
                      Queries public WHO/MedlinePlus references via Gemini API. Uncheck to run 100% locally on-device.
                    </span>
                  </div>
                </label>
              </div>

              {/* Submit Action */}
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || selectedSymptoms.length === 0}
                className="w-full py-2.5 px-4 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl shadow-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span>Evaluating Clinical Evidence & Safety...</span>
                  </>
                ) : (
                  <>
                    <Stethoscope className="w-4 h-4" />
                    <span>{includeGeminiExplanation ? 'Run Evaluation & Grounded Explanation' : 'Run Local Model Evaluation'}</span>
                  </>
                )}
              </button>
            </div>

            {/* Right Column: Prediction Results, Abstention & Safety (7 cols) */}
            <div className="lg:col-span-7 space-y-5">
                {/* Priority 1: Independent Safety Warnings Layer */ }
          {safetyWarnings.length > 0 && (
                <div className="space-y-3">
                  {safetyWarnings.map((w, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-2xl border shadow-xs text-xs space-y-2 ${w.level === 'EMERGENCY'
                          ? 'bg-rose-50 border-rose-300 text-rose-950 ring-2 ring-rose-500/20'
                          : w.level === 'URGENT'
                            ? 'bg-amber-50 border-amber-300 text-amber-950'
                            : 'bg-blue-50 border-blue-200 text-blue-950'
                        }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 font-bold uppercase tracking-wider text-[11px]">
                          {w.level === 'EMERGENCY' ? (
                            <AlertTriangle className="w-4 h-4 text-rose-600 animate-pulse" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-amber-600" />
                          )}
                          <span>{w.level} Safety Advisory: {w.title}</span>
                        </div>
                        {w.emergency_action_recommended && (
                          <span className="px-2 py-0.5 rounded-full font-bold bg-rose-600 text-white text-[10px] inline-flex items-center gap-1">
                            <PhoneCall className="w-3 h-3" />
                            <span>Emergency: 112</span>
                          </span>
                        )}
                      </div>
                      <p className="leading-relaxed font-medium">
                        {w.message}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {!explainResult && !predictResult && !isSubmitting && (
                <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mx-auto">
                    <Info className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">Awaiting Symptom Checklist</h3>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                    Select your observed symptoms from the left panel and click
                    <strong> Run Evaluation</strong> to check for safety red flags and view differential indications.
                  </p>
                </div>
              )}

              {isSubmitting && (
                <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4">
                  <div className="w-10 h-10 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Processing Clinical Pipeline</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      1. Triaging red-flag emergency symptoms independently...<br />
                      2. Evaluating model confidence and evidence sufficiency thresholds...<br />
                      3. {includeGeminiExplanation ? 'Querying medical references and synthesizing grounded context...' : 'Finalizing local inference scores...'}
                    </p>
                  </div>
                </div>
              )}

                {/* Model Abstention / Insufficient Information State */ }
          {(explainResult || predictResult) && isAbstained && (
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                    <ShieldAlert className="w-5 h-5 text-indigo-600" />
                    <span>Model Abstained: Insufficient Symptom Information</span>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs text-slate-700 leading-relaxed space-y-2">
                    <p>
                      <strong>Why did the model abstain?</strong> {abstentionReason || explainResult?.explanation}
                    </p>
                    <p className="text-slate-500">
                      To prevent generating misleading differential suggestions, the machine-learning pipeline requires at least 3 distinct clinical features. Please consult a licensed medical practitioner for personalized assessment.
                    </p>
                  </div>
                </div>
              )}

              {/* Active Predictions Display (When evidence is sufficient or flagged low-confidence) */}
              {(explainResult || predictResult) && activePredictions.length > 0 && (
                <div className="space-y-5">
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Experimental Model Differential Rankings</h3>
                        <p className="text-[11px] text-slate-500">
                          Evaluated on server using {explainResult?.model_identifier || predictResult?.model_identifier}
                        </p>
                      </div>
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${evidenceStatus === 'SUFFICIENT_EVIDENCE'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-amber-50 text-amber-700'
                          }`}>
                          {evidenceStatus === 'SUFFICIENT_EVIDENCE' ? 'Sufficient Model Evidence' : 'Low Confidence Prediction'}
                        </span>
                    </div>

                    <div className="space-y-2.5">
                        {
                          activePredictions.map(pred => {
                            const scorePct = Math.round(pred.experimental_model_score * 100);
                            return (
                              <div
                                key={pred.rank}
                                className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 flex items-center justify-between"
                              >
                                <div className="flex items-center gap-3">
                                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${pred.rank === 1 ? 'bg-teal-600 text-white' : 'bg-slate-200 text-slate-700'
                                    }`}>
                                    {pred.rank}
                                  </span>
                                  <div>
                                    <span className="text-xs font-bold text-slate-900 block">
                                      {pred.disease_category}
                                    </span>
                                    <span className="text-[10px] text-slate-500">
                                      Rank {pred.rank} in experimental differential
                                    </span>
                                  </div>
                                </div>

                                <div className="text-right">
                                  <span className="text-xs font-bold text-teal-700">
                                    {scorePct}%
                                  </span>
                                  <span className="text-[10px] text-slate-400 block">
                                    model score: {pred.experimental_model_score.toFixed(4)}
                                  </span>
                                </div>
                              </div>
                            );
                          })
                        }
                </div>
                  </div>

                    {/* Grounded Gemini Explanation Card (Only when explanation was requested and present) */}
                    {explainResult && explainResult.explanation && (
                      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                            <BookOpen className="w-4 h-4 text-indigo-600" />
                            <span>Evidence-Grounded Clinical Reference Explanation</span>
                          </h3>
                        </div>

                        <div className="text-xs text-slate-700 leading-relaxed bg-slate-50/50 p-4 rounded-xl border border-slate-100 whitespace-pre-line">
                          {explainResult.explanation}
                        </div>

                                      {/* Citations List */}
                                      {explainResult.citations.length > 0 && (
                                        <div className="space-y-2">
                                          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                                            Supporting Clinical References
                                          </span>
                                          <div className="space-y-1.5">
                                            {explainResult.citations.map((c, i) => (
                                              <div
                                                key={i}
                                                className="p-3 rounded-lg border border-slate-100 bg-white text-xs flex items-start justify-between gap-3"
                                              >
                                                <div>
                                                  <div className="flex items-center gap-1.5 font-medium text-slate-900">
                                                    <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                                                    <span>{c.title || c.document_id}</span>
                                                  </div>
                                                  <p className="text-[11px] text-slate-500 mt-0.5">
                                                    {c.source_organization} {c.section_heading ? `• ${c.section_heading}` : ''}
                                                  </p>
                                                </div>
                                                {c.source_url && (
                                                  <a
                                                    href={c.source_url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="text-teal-600 hover:text-teal-700 shrink-0 inline-flex items-center gap-1 text-[11px] font-semibold"
                                                  >
                                                    <span>Official Doc</span>
                                                    <ExternalLink className="w-3 h-3" />
                                                  </a>
                                                )}
                                              </div>
                        ))}
                                        </div>
                    </div>
                  )}

                                    {/* Latency & Telemetry */}
                                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                                      <span className="flex items-center gap-1">
                                        <Clock className="w-3.5 h-3.5" />
                                        <span>Total Latency: {(explainResult.total_latency_ms / 1000).toFixed(2)}s</span>
                                      </span>
                                      <span>Pinecone: {explainResult.retrieval_latency_ms.toFixed(0)}ms | Gemini: {explainResult.generation_latency_ms.toFixed(0)}ms</span>
                                    </div>
                                    </div>
              )}
                                </div>
                              )}
                            </div>
                          </div>
    </div>
                    );
};
