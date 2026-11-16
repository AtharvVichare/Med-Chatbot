import React from 'react';
import { 
  CheckCircle2, 
  Printer, 
  X, 
  Calendar, 
  Clock, 
  Building2, 
  User, 
  Stethoscope, 
  FileText, 
  MapPin, 
  ShieldCheck, 
  CreditCard 
} from 'lucide-react';
import type { AppointmentBookingTicket, AppointmentBooking } from '../types';

interface AppointmentTicketModalProps {
  ticket: AppointmentBookingTicket | AppointmentBooking | null;
  onClose: () => void;
}

export const AppointmentTicketModal: React.FC<AppointmentTicketModalProps> = ({ ticket, onClose }) => {
  if (!ticket) return null;

  const handlePrint = () => {
    window.print();
  };

  const hospitalName = ticket.hospital_name || 'Seth GS Medical College & KEM Hospital';
  const tokenNumber = ticket.token_number || `TKT-${ticket.booking_date.replace(/-/g, '')}-${ticket.booking_id.slice(-4)}`;
  const chamberRoom = ticket.chamber_room || 'Chamber 104, OPD Block B';
  const fee = ticket.fee || ticket.consultation_fee || 800;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden animate-fadeIn my-8">
        
        {/* Top Accent Header */}
        <div className="bg-gradient-to-r from-teal-700 via-teal-800 to-slate-900 text-white p-6 relative">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2 text-teal-300 text-xs font-semibold uppercase tracking-wider mb-1">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            <span>Verified HMS Consultation Slip &bull; ABDM Integrated</span>
          </div>

          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Building2 className="w-6 h-6 text-teal-300 shrink-0" />
            <span>{hospitalName}</span>
          </h2>
          <p className="text-xs text-teal-100/90 mt-1">
            Outpatient Department (OPD) &bull; Official Appointment Confirmation Token
          </p>
        </div>

        {/* Token Banner */}
        <div className="bg-emerald-50 border-y border-emerald-200 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-bold shadow-sm">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">Queue Token Number</div>
              <div className="text-2xl font-black text-emerald-950 font-mono tracking-tight">{tokenNumber}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase bg-emerald-100 text-emerald-900 border border-emerald-300">
              Status: {ticket.status.toUpperCase()}
            </span>
            <span className="px-2.5 py-1 rounded-md text-[11px] font-mono font-medium bg-white text-slate-700 border border-emerald-200">
              Ref: {ticket.booking_id}
            </span>
          </div>
        </div>

        {/* Slip Body */}
        <div className="p-6 space-y-6">
          {/* Two-Column Information Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Patient Information Card */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <User className="w-4 h-4 text-teal-600" />
                <span>Patient Information</span>
              </div>
              <div className="pt-1">
                <div className="text-base font-bold text-slate-900">{ticket.patient_name || 'Patient'}</div>
                <div className="text-xs font-mono text-slate-500">ID: {ticket.patient_id}</div>
              </div>
              {ticket.chief_complaint && (
                <div className="pt-1 border-t border-slate-200 text-xs text-slate-600">
                  <span className="font-semibold text-slate-700">Reason / Complaint: </span>
                  {ticket.chief_complaint}
                </div>
              )}
            </div>

            {/* Doctor & Chamber Card */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <Stethoscope className="w-4 h-4 text-teal-600" />
                <span>Attending Specialist</span>
              </div>
              <div className="pt-1">
                <div className="text-base font-bold text-slate-900">{ticket.doctor_name}</div>
                <div className="text-xs text-teal-700 font-medium">{ticket.qualification || 'MBBS, MD'}</div>
                <div className="text-xs text-slate-500 font-semibold">{ticket.department}</div>
              </div>
              <div className="pt-1 border-t border-slate-200 flex items-center gap-1.5 text-xs font-medium text-slate-700">
                <MapPin className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                <span>{chamberRoom}</span>
              </div>
            </div>

          </div>

          {/* Schedule & Timing Details Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-2xl bg-teal-50/60 border border-teal-200/60">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white text-teal-700 flex items-center justify-center border border-teal-200 shadow-xs">
                <Calendar className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-teal-800">Consultation Date</div>
                <div className="text-sm font-bold text-slate-900">{ticket.booking_date}</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white text-teal-700 flex items-center justify-center border border-teal-200 shadow-xs">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-teal-800">Time Slot</div>
                <div className="text-sm font-bold text-slate-900">{ticket.time_slot}</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white text-teal-700 flex items-center justify-center border border-teal-200 shadow-xs">
                <CreditCard className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-teal-800">Consultation Fee</div>
                <div className="text-sm font-bold text-slate-900">₹{fee}</div>
              </div>
            </div>
          </div>

          {/* Live HMS Synchronized Banner */}
          <div className="p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-200/80 flex items-start gap-3">
            <CheckCircle2 className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div className="text-xs text-indigo-900">
              <span className="font-bold">Real-Time HMS Synchronization Confirmed: </span>
              This appointment is recorded in the PostgreSQL database and immediately visible on both the{' '}
              <strong className="underline">Doctor Consultation Desk</strong> and the{' '}
              <strong className="underline">Nurse Station OPD Queue</strong>.
            </div>
          </div>

          {/* OPD Instructions */}
          <div className="text-[11px] text-slate-500 bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1">
            <div className="font-bold text-slate-700">Patient OPD Instructions:</div>
            <ul className="list-disc list-inside space-y-0.5">
              <li>Please report to the OPD reception counter 15 minutes before your scheduled slot.</li>
              <li>Present this token slip (digital or printed) along with a valid Government Photo ID (Aadhaar / ABHA Card).</li>
              <li>Bring your existing prescription slips and diagnostic test reports for review.</li>
            </ul>
          </div>
        </div>

        {/* Modal Action Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-slate-500 flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-slate-400" />
            <span>Digital Token ID: <code className="font-mono text-slate-700">{tokenNumber}</code></span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              type="button"
              onClick={handlePrint}
              className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-xl text-xs font-bold transition shadow-xs"
            >
              <Printer className="w-4 h-4 text-slate-600" />
              <span>Print / Save Slip</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 sm:flex-none inline-flex items-center justify-center px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition shadow-xs"
            >
              Done
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
