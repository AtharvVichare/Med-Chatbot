import React, { useState, useEffect } from 'react';
import { 
  Receipt, 
  CheckCircle2, 
  CreditCard, 
  RefreshCw 
} from 'lucide-react';
import { api } from '../services/api';
import type { BillingInvoice } from '../types';

export const BillingPage: React.FC = () => {
  const [invoices, setInvoices] = useState<BillingInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [paymentNotice, setPaymentNotice] = useState<string | null>(null);

  const loadInvoices = async () => {
    setLoading(true);
    try {
      const data = await api.listInvoices();
      setInvoices(data);
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, []);

  const handlePay = async (invoiceId: string) => {
    try {
      const res = await api.payInvoice(invoiceId, 'online_upi');
      setPaymentNotice(res.message);
      loadInvoices();
      setTimeout(() => setPaymentNotice(null), 4000);
    } catch (err: any) {
      alert(`Payment failed: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Receipt className="w-6 h-6 text-teal-600" />
            Patient Invoices & Revenue Cycle Management (RCM)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Itemized charges for consultations, procedures, beds, ICD-10 assisted coding, and instant settlement.
          </p>
        </div>
        <button
          onClick={loadInvoices}
          className="p-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl transition self-start sm:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {paymentNotice && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center gap-3 text-sm animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{paymentNotice}</span>
        </div>
      )}

      <div className="space-y-4">
        {invoices.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
            <Receipt className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">No Invoices on Record</p>
          </div>
        ) : (
          invoices.map((inv) => {
            const isPaid = inv.payment_status === 'paid';
            return (
              <div key={inv.invoice_id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:border-teal-200 transition">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3 mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-base">{inv.invoice_id}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        isPaid ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {inv.payment_status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Patient: <b>{inv.patient_name || inv.patient_id}</b> &bull; Date: {inv.invoice_date}
                    </p>
                  </div>

                  <div className="text-right">
                    <div className="text-xl font-extrabold text-slate-900">
                      ₹{inv.patient_payable.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                    <p className="text-[11px] text-slate-400">
                      (Total ₹{inv.total_amount.toLocaleString('en-IN')} &bull; Insured ₹{inv.insurance_covered.toLocaleString('en-IN')})
                    </p>
                  </div>
                </div>

                {/* Line Items */}
                <div className="space-y-1.5 mb-4 text-xs">
                  <div className="font-semibold text-slate-700 mb-1">Itemized Charges:</div>
                  {inv.items.map((it, idx) => (
                    <div key={idx} className="flex justify-between py-1 border-b border-slate-50 text-slate-600">
                      <span>{it.description} <span className="text-[10px] text-slate-400">({it.category})</span></span>
                      <span className="font-medium text-slate-900">₹{it.amount.toLocaleString('en-IN')}</span>
                    </div>
                  ))}
                </div>

                {/* Assisted ICD-10 Codes */}
                {inv.icd10_codes?.length > 0 && (
                  <div className="p-3 bg-slate-50 rounded-xl mb-4 border border-slate-100 text-xs">
                    <span className="font-bold text-indigo-700 block mb-1">Assisted ICD-10 Diagnostic Codes:</span>
                    <div className="flex flex-wrap gap-2">
                      {inv.icd10_codes.map((code, cidx) => (
                        <span key={cidx} className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-mono text-[11px]">
                          <b>{code.code}</b>: {code.description}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between pt-2">
                  <div className="text-[11px] text-slate-400">
                    Coded by: <span className="font-semibold text-slate-600">{inv.coded_by || 'Billing/RCM Agent'}</span>
                  </div>
                  {!isPaid && (
                    <button
                      onClick={() => handlePay(inv.invoice_id)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-semibold transition shadow-sm"
                    >
                      <CreditCard className="w-4 h-4" />
                      <span>Pay Balance (₹{inv.patient_payable.toLocaleString('en-IN')})</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
