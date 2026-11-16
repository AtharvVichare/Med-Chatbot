import React, { useState, useEffect } from 'react';
import { 
  BedDouble, 
  Package, 
  DollarSign, 
  Bot, 
  Search, 
  CheckCircle2, 
  RefreshCw,
  Sparkles,
  FileCheck2
} from 'lucide-react';
import { api } from '../services/api';
import type { BedOverview, PurchaseOrder, AgentEvent, BIQueryResult } from '../types';

export const ManagementDashboardPage: React.FC = () => {
  const [bedOverview, setBedOverview] = useState<BedOverview | null>(null);
  const [inventoryAudit, setInventoryAudit] = useState<any>(null);
  const [revenueSummary, setRevenueSummary] = useState<any>(null);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const [biQuery, setBiQuery] = useState('');
  const [biResult, setBiResult] = useState<BIQueryResult | null>(null);
  const [isBiLoading, setIsBiLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [beds, invAudit, rev, orders, events] = await Promise.all([
        api.getBedOverview(),
        api.auditInventory(),
        api.getRevenueSummary(),
        api.listPurchaseOrders(),
        api.listAgentEvents(30)
      ]);
      setBedOverview(beds);
      setInventoryAudit(invAudit);
      setRevenueSummary(rev);
      setPurchaseOrders(orders);
      setAgentEvents(events);
    } catch (err) {
      console.error('Error loading management dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleRunBIQuery = async (queryText?: string) => {
    const q = queryText || biQuery;
    if (!q.trim()) return;
    setIsBiLoading(true);
    try {
      const res = await api.runConversationalBI(q);
      setBiResult(res);
      setBiQuery(q);
    } catch (err: any) {
      alert(`BI Query failed: ${err.message}`);
    } finally {
      setIsBiLoading(false);
    }
  };

  const handleAuthorizePO = async (poId: string, action: 'approve' | 'reject') => {
    try {
      await api.authorizePurchaseOrder(poId, action, `Action taken by hospital administrator`);
      setActionSuccess(`Purchase Order ${poId} ${action === 'approve' ? 'Authorized' : 'Rejected'} successfully.`);
      const updatedOrders = await api.listPurchaseOrders();
      setPurchaseOrders(updatedOrders);
      const events = await api.listAgentEvents(30);
      setAgentEvents(events);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(`Error updating PO: ${err.message}`);
    }
  };

  const sampleBIQueries = [
    "What is today's bed occupancy?",
    "Show medicines running low in inventory",
    "What is our revenue this week?",
    "How many appointments are booked?"
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 rounded-2xl text-white shadow-lg">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 text-xs font-bold bg-teal-500/20 text-teal-300 rounded-full border border-teal-500/30">
              100-Bed Tertiary Facility
            </span>
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">
              AI-Native Orchestration
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Hospital Executive & Operations Dashboard</h1>
          <p className="text-sm text-slate-300">
            Real-time capacity, autonomous procurement, financial intelligence, and multi-agent coordination.
          </p>
        </div>
        <button
          onClick={loadAllData}
          className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-sm font-medium transition backdrop-blur-sm self-start md:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Live Feeds</span>
        </button>
      </div>

      {actionSuccess && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center gap-3 text-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Bed Capacity Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Facility Occupancy</span>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <BedDouble className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{bedOverview?.occupancy_rate}%</span>
            <span className="text-xs text-slate-500">
              ({bedOverview?.occupied_beds}/{bedOverview?.total_beds} beds)
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 mt-3 overflow-hidden">
            <div 
              className={`h-2 rounded-full ${
                (bedOverview?.occupancy_rate || 0) > 85 ? 'bg-rose-500' : (bedOverview?.occupancy_rate || 0) > 70 ? 'bg-amber-500' : 'bg-teal-500'
              }`}
              style={{ width: `${bedOverview?.occupancy_rate || 0}%` }}
            ></div>
          </div>
          <p className="text-xs text-slate-500 mt-2 flex justify-between">
            <span>Ready: {bedOverview?.available_beds} beds</span>
            <span>Cleaning: {bedOverview?.cleaning_beds}</span>
          </p>
        </div>

        {/* Procurement Alerts Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Inventory Status</span>
            <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
              <Package className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-600">{inventoryAudit?.critical_count || 0}</span>
            <span className="text-xs text-slate-500 font-medium">Critical Shortages</span>
          </div>
          <p className="text-xs text-slate-600 mt-3 flex items-center justify-between">
            <span>Low Stock: <b>{inventoryAudit?.low_stock_count || 0}</b></span>
            <span>Expiring (90d): <b>{inventoryAudit?.expiring_count || 0}</b></span>
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Autonomous PO drafts awaiting review</p>
        </div>

        {/* Revenue Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Billed Revenue</span>
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-slate-900">
              ₹{(revenueSummary?.total_billed || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-600 mt-3">
            <span>Collected: <b>₹{(revenueSummary?.total_collected || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</b></span>
            <span className="text-emerald-600 font-bold">{revenueSummary?.collection_rate}%</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Pending: ₹{(revenueSummary?.pending_collections || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
        </div>

        {/* Autonomous AI Agents Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">AI Agents Active</span>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Bot className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-indigo-600">6</span>
            <span className="text-xs text-slate-500 font-medium">Autonomous Agents</span>
          </div>
          <p className="text-xs text-slate-600 mt-3 flex items-center justify-between">
            <span>Event Bus: <b className="text-teal-600">Online</b></span>
            <span>Escalations: <b>{agentEvents.filter(e => e.requires_human_approval && e.approval_status === 'pending').length}</b></span>
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Intake &bull; Scheduling &bull; Pharmacy &bull; Procurement &bull; RCM &bull; BI</p>
        </div>
      </div>

      {/* Conversational BI Agent Natural Language Search Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <h2 className="text-base font-bold text-slate-900">Conversational BI Agent (Natural Language to SQL & Analytics)</h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Ask questions in plain English. The agent converts requests into safe database queries and visualizes operational KPIs.
        </p>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3.5 text-slate-400" />
            <input
              type="text"
              value={biQuery}
              onChange={(e) => setBiQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRunBIQuery()}
              placeholder="e.g. What is today's bed occupancy? or Show medicines running low in inventory"
              className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>
          <button
            onClick={() => handleRunBIQuery()}
            disabled={isBiLoading || !biQuery.trim()}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl text-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isBiLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            <span>Analyze</span>
          </button>
        </div>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Suggested:</span>
          {sampleBIQueries.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleRunBIQuery(q)}
              className="px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition"
            >
              {q}
            </button>
          ))}
        </div>

        {/* BI Query Result Box */}
        {biResult && (
          <div className="mt-5 p-5 bg-slate-50 rounded-xl border border-indigo-100 animate-fadeIn">
            <div className="flex items-center justify-between mb-3 border-b border-slate-200/60 pb-2">
              <span className="text-xs font-bold text-indigo-700 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                BI Query Synthesis: {biResult.domain.replace('_', ' ').toUpperCase()}
              </span>
              <span className="text-xs text-slate-400">Validated Safe SQL Aggregation</span>
            </div>
            
            <div className="prose prose-sm max-w-none text-slate-800 leading-relaxed whitespace-pre-line text-sm">
              {biResult.summary}
            </div>

            {/* Structured Chart Visualization if applicable */}
            {biResult.chart && (
              <div className="mt-4 p-4 bg-white rounded-lg border border-slate-200">
                <h4 className="text-xs font-bold text-slate-700 mb-3">{biResult.chart.title}</h4>
                <div className="space-y-2">
                  {biResult.chart.labels.map((lbl, i) => {
                    const val = biResult.chart?.data 
                      ? biResult.chart.data[i] 
                      : (biResult.chart?.series?.[0]?.data?.[i] || 0);
                    return (
                      <div key={i} className="flex items-center gap-3 text-xs">
                        <span className="w-32 font-medium text-slate-600 truncate">{lbl}:</span>
                        <div className="flex-1 bg-slate-100 h-3 rounded-full overflow-hidden">
                          <div 
                            className="bg-indigo-600 h-3 rounded-full transition-all"
                            style={{ width: `${Math.min(100, (Number(val) / 20) * 100)}%` }}
                          ></div>
                        </div>
                        <span className="font-bold text-slate-900 w-12 text-right">{val}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Ward Occupancy & Capacity Grid (10 Wards) */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">100-Bed Facility Ward Breakdown</h2>
            <p className="text-xs text-slate-500">Live ward availability, occupancy rates, and bed types.</p>
          </div>
          <span className="text-xs font-bold text-teal-700 bg-teal-50 px-3 py-1 rounded-full border border-teal-200">
            10 Care Units
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          {bedOverview?.wards.map((w, idx) => {
            const occPct = Math.round((w.occupied / w.total) * 100);
            return (
              <div key={idx} className="p-4 bg-slate-50 rounded-xl border border-slate-200 hover:border-teal-300 transition">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold text-slate-900 truncate">{w.ward}</h3>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    occPct > 85 ? 'bg-rose-100 text-rose-700' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {occPct}%
                  </span>
                </div>
                <div className="text-xl font-extrabold text-slate-900 mb-1">
                  {w.occupied} <span className="text-xs font-normal text-slate-500">/ {w.total} beds</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mb-2 overflow-hidden">
                  <div 
                    className={`h-1.5 rounded-full ${occPct > 85 ? 'bg-rose-500' : 'bg-teal-600'}`}
                    style={{ width: `${occPct}%` }}
                  ></div>
                </div>
                <p className="text-[11px] text-teal-700 font-medium">
                  {w.available} available bed{w.available !== 1 ? 's' : ''}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Procurement & Purchase Orders Authorization Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-indigo-600" />
                Autonomous Purchase Order Drafts
              </h2>
              <p className="text-xs text-slate-500">Drafted by Procurement Agent requiring executive approval.</p>
            </div>
            <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-full">
              {purchaseOrders.filter(p => p.status === 'draft_pending_authorization').length} Pending
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-96 pr-1">
            {purchaseOrders.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No purchase orders drafted.</p>
            ) : (
              purchaseOrders.map((po) => {
                const isPending = po.status === 'draft_pending_authorization';
                return (
                  <div key={po.po_id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-slate-900">{po.po_id}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        isPending ? 'bg-amber-100 text-amber-800' : po.status === 'approved' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                      }`}>
                        {po.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 font-semibold">{po.item_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Quantity: <b>{po.quantity} {po.unit}</b> &bull; Supplier: {po.supplier_name}
                    </p>
                    <p className="text-xs font-bold text-slate-900 mt-1">
                      Est. Total: ₹{po.estimated_cost.toLocaleString('en-IN')}
                    </p>
                    {po.approval_notes && (
                      <p className="text-[11px] text-amber-800 bg-amber-50/80 p-2 rounded mt-2 border border-amber-200/50">
                        {po.approval_notes}
                      </p>
                    )}
                    {isPending && (
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleAuthorizePO(po.po_id, 'approve')}
                          className="flex-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition"
                        >
                          Authorize Purchase
                        </button>
                        <button
                          onClick={() => handleAuthorizePO(po.po_id, 'reject')}
                          className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg text-xs font-medium transition"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Live Multi-Agent Event Bus Stream */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Bot className="w-5 h-5 text-teal-600" />
                Agent Event Bus Activity Stream
              </h2>
              <p className="text-xs text-slate-500">Live inter-agent communications and workflow coordination.</p>
            </div>
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Bus
            </span>
          </div>

          <div className="space-y-2.5 flex-1 overflow-y-auto max-h-96 pr-1 font-mono text-xs">
            {agentEvents.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No events emitted on bus yet.</p>
            ) : (
              agentEvents.map((ev) => (
                <div key={ev.event_id} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-indigo-700">{ev.event_type}</span>
                    <span className="text-[10px] text-slate-400">
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-600 text-[11px]">
                    <span className="font-semibold text-teal-700">{ev.source_agent}</span>
                    <span>&rarr;</span>
                    <span className="font-semibold text-slate-700">{ev.target_agent || 'BROADCAST'}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500 truncate">
                    {typeof ev.payload === 'object' ? JSON.stringify(ev.payload) : ev.payload}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
