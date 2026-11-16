import React from 'react';
import { 
  CheckCircle2, 
  Loader2, 
  Building2, 
  Stethoscope, 
  ShieldCheck, 
  Server
} from 'lucide-react';

export interface BookingProgressStep {
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed';
}

interface BookingProgressModalProps {
  isOpen: boolean;
  doctorName: string;
  hospitalName: string;
  department: string;
  bookingDate: string;
  timeSlot: string;
  currentStep: number; // 0 to 4
  steps: BookingProgressStep[];
}

export const BookingProgressModal: React.FC<BookingProgressModalProps> = ({
  isOpen,
  doctorName,
  hospitalName,
  department,
  bookingDate,
  timeSlot,
  currentStep,
  steps
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden animate-scaleUp">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-800 to-slate-900 text-white p-6">
          <div className="flex items-center gap-2 text-teal-300 text-xs font-semibold uppercase tracking-wider mb-1">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            <span>HMS Multi-Agent Real-Time Booking Workflow</span>
          </div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Processing Consultation Booking</span>
          </h3>
          <p className="text-xs text-teal-100/80 mt-1">
            Coordinating intake triage, slot reservation, and hospital console dispatch.
          </p>
        </div>

        {/* Doctor & Hospital Target Preview */}
        <div className="bg-slate-50 border-b border-slate-200 p-4 grid grid-cols-2 gap-3 text-xs">
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-400">Attending Specialist</div>
            <div className="font-bold text-slate-900 flex items-center gap-1.5 mt-0.5">
              <Stethoscope className="w-3.5 h-3.5 text-teal-600" />
              <span>{doctorName}</span>
            </div>
            <div className="text-[11px] text-teal-700 font-medium">{department}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-400">Hospital Facility</div>
            <div className="font-semibold text-slate-800 flex items-center gap-1.5 mt-0.5 truncate" title={hospitalName}>
              <Building2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
              <span className="truncate">{hospitalName}</span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5 flex items-center gap-2">
              <span>{bookingDate}</span>
              <span>&bull;</span>
              <strong className="text-teal-700">{timeSlot}</strong>
            </div>
          </div>
        </div>

        {/* Workflow Progression Steps */}
        <div className="p-6 space-y-4">
          {steps.map((s, idx) => {
            const isCompleted = idx < currentStep || s.status === 'completed';
            const isCurrent = idx === currentStep && s.status === 'running';

            return (
              <div 
                key={idx} 
                className={`flex items-start gap-3.5 p-3 rounded-xl border transition-all ${
                  isCompleted 
                    ? 'bg-emerald-50/60 border-emerald-200/80' 
                    : isCurrent 
                    ? 'bg-teal-50/80 border-teal-300 ring-2 ring-teal-500/20' 
                    : 'bg-slate-50/40 border-slate-200/60 opacity-60'
                }`}
              >
                <div className="mt-0.5 shrink-0">
                  {isCompleted ? (
                    <div className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-xs">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  ) : isCurrent ? (
                    <div className="w-6 h-6 rounded-full bg-teal-600 text-white flex items-center justify-center animate-spin">
                      <Loader2 className="w-4 h-4" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center font-bold text-xs">
                      {idx + 1}
                    </div>
                  )}
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div className={`text-xs font-bold ${isCompleted ? 'text-emerald-950' : isCurrent ? 'text-teal-950' : 'text-slate-600'}`}>
                      {s.title}
                    </div>
                    {isCurrent && (
                      <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider animate-pulse">
                        Verifying...
                      </span>
                    )}
                    {isCompleted && (
                      <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">
                        Confirmed
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                    {s.description}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-3.5 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span>PostgreSQL HMS Live Transaction &bull; Token Issuance</span>
          </div>
          <span className="font-semibold text-teal-700">Step {Math.min(currentStep + 1, steps.length)} of {steps.length}</span>
        </div>

      </div>
    </div>
  );
};
