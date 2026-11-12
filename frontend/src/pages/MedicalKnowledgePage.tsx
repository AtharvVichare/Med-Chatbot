import React, { useState } from 'react';
import { 
  BookOpen, 
  AlertCircle, 
  CheckCircle2, 
  ExternalLink, 
  ShieldAlert, 
  Clock, 
  ArrowRight,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import type { MedicalAskResponse } from '../types';

export const MedicalKnowledgePage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MedicalAskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sampleQueries = [
    "What are the diagnostic fasting blood glucose criteria for diabetes?",
    "What systolic numbers define Stage 2 hypertension?",
    "What are the four pillars of guideline-directed medical therapy in heart failure?",
    "What are the warning signs of severe dengue that require hospital admission?"
  ];

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q) {
      setError('Please enter a clinical reference question.');
      return;
    }

    if (queryText) {
      setQuestion(queryText);
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.askMedicalKnowledge(q, 3);
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve grounded reference response.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-600" />
          <span>Evidence-Grounded Medical Reference RAG</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Query verified medical clinical guidelines (WHO & MedlinePlus) indexed in Pinecone (v2 namespace) 
          and synthesized with Gemini 3.5 Flash Lite under strict non-extrapolation constraints.
        </p>
      </div>

      {/* Safety Notice */}
      <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-200/60 text-indigo-950 text-xs flex items-start gap-2.5">
        <Info className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
        <div className="leading-relaxed">
          <strong>Public Reference Boundary:</strong> This service queries public clinical guidelines across 
          12 approved domains. It has zero access to individual patient EHRs. In acute life-threatening situations, 
          the system will immediately escalate to national emergency directives.
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Query Input Card */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="relative">
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a medical guideline question (e.g. diagnostic criteria, first-line medications, WHO staging)..."
            className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
            <span className="font-semibold text-slate-700">Quick Samples:</span>
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                onClick={() => handleAsk(sq)}
                className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-600 truncate max-w-xs transition-colors"
              >
                {sq}
              </button>
            ))}
          </div>

          <button
            onClick={() => handleAsk()}
            disabled={isLoading || !question.trim()}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-md transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>Synthesizing...</span>
              </>
            ) : (
              <>
                <span>Retrieve & Answer</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Response Card */}
      {result && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
          {/* Status Badge */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <span className="text-xs font-bold text-slate-900">Clinical Reference Synthesis</span>
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
              result.evidence_status === 'SUFFICIENT' 
                ? 'bg-emerald-50 text-emerald-800' 
                : result.evidence_status === 'EMERGENCY_ESCALATION'
                ? 'bg-rose-100 text-rose-800'
                : 'bg-amber-50 text-amber-800'
            }`}>
              Status: {result.evidence_status}
            </span>
          </div>

          {/* Emergency Directive Banner if flagged */}
          {result.emergency_directive && (
            <div className="p-4 rounded-xl bg-rose-50 border-2 border-rose-300 text-rose-900 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm text-rose-700">
                <ShieldAlert className="w-5 h-5 text-rose-600" />
                <span>CRITICAL EMERGENCY DIRECTIVE</span>
              </div>
              <p className="leading-relaxed whitespace-pre-line">{result.emergency_directive}</p>
            </div>
          )}

          {/* Synthesized Answer */}
          <div className="text-xs text-slate-800 leading-relaxed bg-slate-50/60 p-4 rounded-xl border border-slate-100 whitespace-pre-line">
            {result.answer}
          </div>

          {/* Supporting Citations */}
          {result.citations.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Verified Guideline Chunks ({result.citations.length})
              </span>
              <div className="space-y-2">
                {result.citations.map((c: any, i: number) => (
                  <div key={i} className="p-3 bg-white rounded-xl border border-slate-200 text-xs flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-1.5 font-semibold text-slate-900">
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
                        className="text-indigo-600 hover:text-indigo-800 text-[11px] font-semibold inline-flex items-center gap-1"
                      >
                        <span>View Source</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Telemetry Footer */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Retrieval: {result.retrieval_latency_ms.toFixed(0)}ms | Generation: {result.generation_latency_ms.toFixed(0)}ms</span>
            </span>
            <span>Model: {result.model_id}</span>
          </div>
        </div>
      )}
    </div>
  );
};
