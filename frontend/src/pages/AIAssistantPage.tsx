import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Bot, 
  Send, 
  Plus, 
  Paperclip,
  User, 
  Sparkles, 
  CheckCircle2, 
  Activity, 
  Heart, 
  MessageSquare,
  TrendingUp,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { ChatConversation, ChatMessage } from '../types';

export const AIAssistantPage: React.FC = () => {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputContent, setInputContent] = useState('');
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);

  // Plus Action Drawer State
  const [showActionDrawer, setShowActionDrawer] = useState(false);
  const [selectedAction, setSelectedAction] = useState<'symptoms' | 'measurement' | 'medication' | null>(null);

  // Quick symptom selector state
  const [availableSymptoms, setAvailableSymptoms] = useState<string[]>([]);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [symptomSearch, setSymptomSearch] = useState('');

  // Quick measurement state
  const [measureType, setMeasureType] = useState('blood_pressure');
  const [measureVal1, setMeasureVal1] = useState('');
  const [measureVal2, setMeasureVal2] = useState('');

  // Staged file attachment state (not uploaded until user hits Send)
  const [stagedFile, setStagedFile] = useState<File | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversations on mount
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const convs = await api.getConversations();
        setConversations(convs);
        if (convs.length > 0) {
          setActiveConversationId(convs[0].conversation_id);
        } else {
          // Create initial conversation
          const newConv = await api.createConversation('Initial Health Consultation');
          setConversations([newConv]);
          setActiveConversationId(newConv.conversation_id);
        }
      } catch (err) {
        console.error('Failed to load conversations:', err);
      }
    };

    const fetchSymptoms = async () => {
      try {
        const list = await api.getSymptomsList();
        setAvailableSymptoms(list);
      } catch (e) {}
    };

    fetchConversations();
    fetchSymptoms();
  }, []);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConversationId) return;
    const fetchMessages = async () => {
      setLoadingMessages(true);
      try {
        const msgs = await api.getConversationMessages(activeConversationId);
        setMessages(msgs);
      } catch (err) {
        console.error('Failed to fetch messages:', err);
      } finally {
        setLoadingMessages(false);
      }
    };
    fetchMessages();
  }, [activeConversationId]);

  const handleCreateNewConversation = async () => {
    try {
      const newConv = await api.createConversation('New Health Consultation');
      setConversations([newConv, ...conversations]);
      setActiveConversationId(newConv.conversation_id);
      setMessages([]);
    } catch (err: any) {
      alert(err.message || 'Failed to create new conversation');
    }
  };

  const handleSendMessage = async (e?: React.FormEvent, customText?: string) => {
    if (e) e.preventDefault();
    const textToSend = customText || inputContent;
    const fileToUpload = stagedFile;

    // Must have either text or a staged file, and an active conversation
    if ((!textToSend.trim() && !fileToUpload) || !activeConversationId || sending) return;

    setSending(true);

    // If there is a staged file, upload it first
    if (fileToUpload && user?.patient_id) {
      const optimisticUploadMsg: ChatMessage = {
        message_id: 'temp-doc-' + Date.now(),
        conversation_id: activeConversationId,
        sender: 'user',
        content: `Attached medical document: ${fileToUpload.name} (${(fileToUpload.size / 1024).toFixed(1)} KB)`,
        is_confirmed_to_ehr: false,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, optimisticUploadMsg]);
      setStagedFile(null);

      try {
        const formData = new FormData();
        formData.append('file', fileToUpload);
        formData.append('patient_id', user.patient_id);
        formData.append('document_type', 'clinical_report');
        await api.uploadPatientDocument(formData);
      } catch (err: any) {
        alert(err.message || 'File upload failed');
        setSending(false);
        return;
      }
    }

    // Determine user prompt to send
    const promptToSend = textToSend.trim()
      ? (fileToUpload
          ? `${textToSend.trim()} (Attached file: ${fileToUpload.name})`
          : textToSend.trim())
      : (fileToUpload
          ? `I have uploaded my medical report '${fileToUpload.name}'. Please analyze what crucial information was extracted and appended to my health record.`
          : '');

    const optimisticUserMessage: ChatMessage = {
      message_id: 'temp-' + Date.now(),
      conversation_id: activeConversationId,
      sender: 'user',
      content: promptToSend,
      is_confirmed_to_ehr: false,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, optimisticUserMessage]);
    setInputContent('');

    try {
      const assistantReply = await api.sendMessage(activeConversationId, promptToSend);
      setMessages(prev => [...prev.filter(m => m.message_id !== optimisticUserMessage.message_id), optimisticUserMessage, assistantReply]);
    } catch (err: any) {
      alert(err.message || 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const handleConfirmAction = async (msg: ChatMessage) => {
    if (!msg.proposed_ehr_actions) return;
    try {
      const proposal = JSON.parse(msg.proposed_ehr_actions);
      await api.confirmAssistantAction({
        message_id: msg.message_id,
        action_type: proposal.action,
        data: proposal.data || {}
      });
      // Mark as confirmed in UI
      setMessages(prev => prev.map(m => m.message_id === msg.message_id ? { ...m, is_confirmed_to_ehr: true } : m));
      alert('Saved! Your electronic health record has been updated.');
    } catch (err: any) {
      alert(err.message || 'Failed to confirm action');
    }
  };

  const handleAddSymptomsToChat = () => {
    if (selectedSymptoms.length === 0) return;
    const formatted = `I am experiencing the following symptoms: ${selectedSymptoms.join(', ')}. Can you evaluate what might be causing them and advise me on what to monitor?`;
    setSelectedAction(null);
    setShowActionDrawer(false);
    setSelectedSymptoms([]);
    // Do not immediately send; insert into input for the user to review or add to
    setInputContent(formatted);
  };

  const handleAddMeasurementToChat = () => {
    let formatted = '';
    if (measureType === 'blood_pressure' && measureVal1 && measureVal2) {
      formatted = `I just measured my blood pressure: ${measureVal1}/${measureVal2} mmHg. Is this reading within safe targets given my medical profile?`;
    } else if (measureType === 'glucose' && measureVal1) {
      formatted = `I recorded a fasting blood glucose reading of ${measureVal1} mg/dL. What does this indicate?`;
    } else if (measureType === 'pulse' && measureVal1) {
      formatted = `My resting heart rate is ${measureVal1} bpm. Should I be concerned?`;
    } else {
      return;
    }
    setSelectedAction(null);
    setShowActionDrawer(false);
    setMeasureVal1('');
    setMeasureVal2('');
    // Do not immediately send; insert into input for user to review, edit, or append to
    setInputContent(formatted);
  };

  const formatMessageTime = (ts: string) => {
    if (!ts) return '';
    try {
      const dateObj = ts.includes('Z') || ts.includes('+') ? new Date(ts) : new Date(ts.replace(' ', 'T') + 'Z');
      return dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-50 overflow-hidden">
      {/* Left Sidebar: Conversations List */}
      <aside className="w-72 bg-white border-r border-slate-200 hidden md:flex md:flex-col shadow-sm">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Health Consultations</span>
          <button
            onClick={handleCreateNewConversation}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-teal-50 text-teal-700 hover:bg-teal-100 rounded-lg text-xs font-semibold transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map(conv => {
            const isActive = conv.conversation_id === activeConversationId;
            return (
              <button
                key={conv.conversation_id}
                onClick={() => setActiveConversationId(conv.conversation_id)}
                className={`w-full text-left p-3 rounded-xl text-xs transition-colors flex items-start gap-2.5 ${
                  isActive
                    ? 'bg-teal-50 text-teal-900 font-semibold border border-teal-200/60'
                    : 'text-slate-600 hover:bg-slate-50 border border-transparent'
                }`}
              >
                <MessageSquare className={`w-4 h-4 shrink-0 mt-0.5 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                <div className="overflow-hidden flex-1">
                  <p className="truncate">{conv.title}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">{new Date(conv.created_at).toLocaleDateString()}</p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="p-3 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-teal-600 shrink-0" />
          <span>Grounded in verified WHO and MedlinePlus guidelines</span>
        </div>
      </aside>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden relative">
        {/* Chat Header */}
        <div className="h-14 px-6 bg-white border-b border-slate-200 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Personal AI Health Assistant</h2>
              <p className="text-[10px] text-teal-700 font-medium">Context: Connected with {user?.patient_id || 'EHR'}</p>
            </div>
          </div>
          <span className="text-[11px] text-slate-400 hidden sm:block">
            Powered by Gemini & Medical Guidelines
          </span>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.length === 0 && !loadingMessages && (
            <div className="max-w-md mx-auto text-center py-12">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mx-auto mb-3">
                <Bot className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-slate-900 text-base">How can I assist your health today?</h3>
              <p className="text-xs text-slate-500 mt-1">
                You can ask questions about lab results, discuss symptoms, or check medication interactions.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">
                <button
                  onClick={() => handleSendMessage(undefined, "Can you review my active medications and check for potential precautions?")}
                  className="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-700 hover:border-teal-300"
                >
                  Review my active medications
                </button>
                <button
                  onClick={() => handleSendMessage(undefined, "What are common lifestyle recommendations for hypertension?")}
                  className="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-700 hover:border-teal-300"
                >
                  Lifestyle tips for blood pressure
                </button>
              </div>
            </div>
          )}

          {messages.map(msg => {
            const isUser = msg.sender === 'user';
            let parsedProposal: any = null;
            if (msg.proposed_ehr_actions) {
              try {
                parsedProposal = JSON.parse(msg.proposed_ehr_actions);
              } catch {}
            }

            return (
              <div
                key={msg.message_id}
                className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold ${
                  isUser ? 'bg-slate-800 text-white' : 'bg-teal-600 text-white'
                }`}>
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                <div className={`space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
                  <div className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    isUser
                      ? 'bg-slate-900 text-white rounded-tr-none'
                      : 'bg-white text-slate-800 border border-slate-200/80 shadow-xs rounded-tl-none'
                  }`}>
                    {isUser ? (
                      <div className="whitespace-pre-line">{msg.content}</div>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-slate prose-headings:font-bold prose-headings:text-slate-900 prose-headings:text-sm prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-strong:text-slate-900">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Embedded Longitudinal Chart Card */}
                  {parsedProposal && (parsedProposal.action_type === 'render_chart' || parsedProposal.action === 'render_chart') && (
                    <div className="p-4 rounded-xl border border-teal-200 bg-white shadow-sm text-xs text-slate-800 space-y-3 w-full max-w-lg">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                        <div className="flex items-center gap-1.5 font-bold text-teal-900">
                          <TrendingUp className="w-4 h-4 text-teal-600" />
                          <span>{parsedProposal.chart_title || 'Longitudinal Physiological Trend'}</span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 bg-teal-50 text-teal-700 rounded-full font-semibold">
                          Verified EHR Data
                        </span>
                      </div>

                      {parsedProposal.points && parsedProposal.points.length > 0 ? (
                        <div className="space-y-3">
                          <div className="h-28 flex items-end gap-2 pt-4 pb-1 px-1 border-b border-slate-100">
                            {parsedProposal.points.map((pt: any, i: number) => {
                              const allVals = parsedProposal.points.map((p: any) => p.value);
                              const maxVal = Math.max(...allVals, 1);
                              const minVal = Math.min(...allVals, 0);
                              const range = maxVal - minVal || 1;
                              const hPct = Math.max(20, Math.min(100, Math.round(((pt.value - minVal) / range) * 70) + 20));
                              return (
                                <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
                                  <span className="text-[9px] font-bold text-slate-700 group-hover:text-teal-700">
                                    {pt.value}
                                  </span>
                                  <div 
                                    style={{ height: `${hPct}%` }} 
                                    className="w-full max-w-[24px] bg-teal-600 group-hover:bg-teal-700 rounded-t"
                                  />
                                  <span className="text-[8px] text-slate-400 truncate w-full text-center">
                                    {pt.date.slice(5)}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-slate-500">
                            <span>Latest: <strong className="text-slate-800">{parsedProposal.latest_value} {parsedProposal.unit}</strong> ({parsedProposal.latest_date})</span>
                            <span className="capitalize text-teal-700 font-semibold">{parsedProposal.change_direction}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-slate-500">No numerical readings recorded.</p>
                      )}
                    </div>
                  )}

                  {/* Embedded Radiological Imaging Scan Card with Spatial Finding Bounding Box */}
                  {parsedProposal && (parsedProposal.action_type === 'render_imaging_scan' || (Array.isArray(parsedProposal) && parsedProposal.some((p: any) => p.action_type === 'render_imaging_scan'))) && (
                    (() => {
                      const scanData = parsedProposal.action_type === 'render_imaging_scan'
                        ? parsedProposal
                        : parsedProposal.find((p: any) => p.action_type === 'render_imaging_scan');
                      if (!scanData) return null;
                      return (
                        <div className="p-4 rounded-xl border border-indigo-200 bg-white shadow-sm text-xs text-slate-800 space-y-3 w-full max-w-lg">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                            <div className="flex items-center gap-1.5 font-bold text-indigo-900">
                              <Sparkles className="w-4 h-4 text-indigo-600" />
                              <span>{scanData.modality || 'Radiological Diagnostic Scan'}</span>
                            </div>
                            <span className="text-[10px] px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-semibold">
                              {scanData.anatomical_region || 'Imaging Finding'}
                            </span>
                          </div>

                          <div className="space-y-2">
                            <p className="text-[11px] font-semibold text-slate-700">Identified Pathologies & Key Areas:</p>
                            <div className="space-y-1.5">
                              {scanData.findings && scanData.findings.map((f: any, idx: number) => {
                                const box = f.box_2d || [];
                                const hasBox = box.length === 4;
                                return (
                                  <div key={idx} className="p-2.5 rounded-lg bg-indigo-50/60 border border-indigo-100 space-y-1">
                                    <div className="flex items-center justify-between">
                                      <span className="font-bold text-indigo-950 text-xs">
                                        • {f.label || `Finding #${idx + 1}`}
                                      </span>
                                      {hasBox && (
                                        <span className="text-[9px] px-1.5 py-0.5 bg-rose-100 text-rose-800 rounded font-mono">
                                          Area [{box[0]}, {box[1]}]
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-[11px] text-slate-600 leading-relaxed">{f.description}</p>
                                  </div>
                                );
                              })}
                            </div>
                          </div>

                          {scanData.differential_considerations && scanData.differential_considerations.length > 0 && (
                            <div className="pt-1 text-[11px] text-slate-600">
                              <span className="font-semibold text-slate-800">Differential Considerations: </span>
                              {scanData.differential_considerations.join(', ')}
                            </div>
                          )}

                          <div className="p-2 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-900">
                            <strong>Note:</strong> AI radiological analysis is for educational assistance. Formal diagnostic reporting requires clinical correlation by a certified radiologist.
                          </div>
                        </div>
                      );
                    })()
                  )}

                  {/* Proposed EHR Action Card (for non-chart proposals like new medication or vitals save) */}
                  {parsedProposal && parsedProposal.action_type !== 'render_chart' && parsedProposal.action !== 'render_chart' && parsedProposal.action_type !== 'render_imaging_scan' && (
                    <div className="p-3.5 rounded-xl border border-teal-200 bg-teal-50/70 text-xs text-slate-800 space-y-2 max-w-md">
                      <div className="flex items-center gap-1.5 font-bold text-teal-900">
                        <Sparkles className="w-4 h-4 text-teal-600" />
                        <span>Proposed EHR Update</span>
                      </div>
                      <div className="text-slate-700">
                        {Array.isArray(parsedProposal) ? (
                          <div className="space-y-1">
                            <span>The assistant recorded the following updates to your record:</span>
                            <ul className="list-disc list-inside space-y-0.5 mt-1 font-medium text-slate-800">
                              {parsedProposal.map((item: any, idx: number) => (
                                <li key={idx}>
                                  {item.summary || item.title || item.type || 'Clinical Observation'}
                                  {item.confidence ? ` (Confidence: ${Math.round(item.confidence * 100)}%)` : ''}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : (
                          <p>
                            {parsedProposal.summary ||
                              `The assistant identified clinical information to record: ${
                                parsedProposal.title || parsedProposal.action || parsedProposal.type || 'Clinical Measurement'
                              }`}
                          </p>
                        )}
                      </div>

                      <div className="pt-1 flex items-center justify-between">
                        {msg.is_confirmed_to_ehr ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Confirmed & Added to Health Record</span>
                          </span>
                        ) : (
                          <button
                            onClick={() => handleConfirmAction(msg)}
                            className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-lg shadow-sm text-xs transition"
                          >
                            Confirm & Save to Health Record
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  <span className={`block text-[10px] text-slate-400 ${isUser ? 'text-right' : 'text-left'}`}>
                    {formatMessageTime(msg.created_at)}
                  </span>
                </div>
              </div>
            );
          })}

          {sending && (
            <div className="flex gap-3 max-w-3xl mr-auto">
              <div className="w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 text-slate-500 text-xs flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-teal-600 animate-bounce"></span>
                <span className="w-2 h-2 rounded-full bg-teal-600 animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-2 h-2 rounded-full bg-teal-600 animate-bounce [animation-delay:0.4s]"></span>
                <span className="ml-1">Reviewing medical references and patient history...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Plus Action Drawer Popup */}
        {showActionDrawer && (
          <div className="absolute bottom-20 left-4 right-4 sm:left-6 sm:right-6 max-w-xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl p-4 z-20 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-slate-800">Quick Clinical Actions</span>
              <button onClick={() => { setShowActionDrawer(false); setSelectedAction(null); }}>
                <X className="w-4 h-4 text-slate-400" />
              </button>
            </div>

            {selectedAction === null && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  onClick={() => setSelectedAction('symptoms')}
                  className="p-3 rounded-xl border border-slate-200 hover:border-teal-400 bg-slate-50 hover:bg-teal-50/50 text-left transition"
                >
                  <Activity className="w-4 h-4 text-teal-600 mb-1" />
                  <p className="font-semibold text-slate-900">Add Symptoms</p>
                  <p className="text-[10px] text-slate-500">Pick from standardized symptom list</p>
                </button>
                <button
                  onClick={() => setSelectedAction('measurement')}
                  className="p-3 rounded-xl border border-slate-200 hover:border-teal-400 bg-slate-50 hover:bg-teal-50/50 text-left transition"
                >
                  <Heart className="w-4 h-4 text-rose-600 mb-1" />
                  <p className="font-semibold text-slate-900">Add Measurement</p>
                  <p className="text-[10px] text-slate-500">Query BP, glucose, or pulse reading</p>
                </button>
              </div>
            )}

            {/* Sub-action: Symptoms Selector */}
            {selectedAction === 'symptoms' && (
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">Select Symptoms:</span>
                  <button onClick={() => setSelectedAction(null)} className="text-[11px] text-teal-600">Back</button>
                </div>
                <input
                  type="text"
                  placeholder="Filter symptoms (e.g., cough, fever)..."
                  value={symptomSearch}
                  onChange={e => setSymptomSearch(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
                <div className="max-h-36 overflow-y-auto flex flex-wrap gap-1.5 p-1 border border-slate-100 rounded-lg">
                  {availableSymptoms
                    .filter(s => s.toLowerCase().includes(symptomSearch.toLowerCase()))
                    .slice(0, 30)
                    .map(sym => {
                      const isSelected = selectedSymptoms.includes(sym);
                      return (
                        <button
                          key={sym}
                          onClick={() => {
                            setSelectedSymptoms(prev =>
                              isSelected ? prev.filter(x => x !== sym) : [...prev, sym]
                            );
                          }}
                          className={`px-2 py-1 rounded-md text-[11px] transition ${
                            isSelected
                              ? 'bg-teal-600 text-white font-medium'
                              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                          }`}
                        >
                          {sym.replace(/_/g, ' ')}
                        </button>
                      );
                    })}
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={handleAddSymptomsToChat}
                    disabled={selectedSymptoms.length === 0}
                    className="px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-semibold disabled:opacity-50"
                  >
                    Insert {selectedSymptoms.length} Symptoms into Input
                  </button>
                </div>
              </div>
            )}

            {/* Sub-action: Measurement */}
            {selectedAction === 'measurement' && (
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">Submit Measurement to Assistant:</span>
                  <button onClick={() => setSelectedAction(null)} className="text-[11px] text-teal-600">Back</button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setMeasureType('blood_pressure')}
                    className={`py-1.5 rounded-lg border font-medium ${
                      measureType === 'blood_pressure' ? 'border-teal-600 bg-teal-50 text-teal-800' : 'border-slate-200'
                    }`}
                  >
                    Blood Pressure
                  </button>
                  <button
                    type="button"
                    onClick={() => setMeasureType('glucose')}
                    className={`py-1.5 rounded-lg border font-medium ${
                      measureType === 'glucose' ? 'border-teal-600 bg-teal-50 text-teal-800' : 'border-slate-200'
                    }`}
                  >
                    Glucose
                  </button>
                  <button
                    type="button"
                    onClick={() => setMeasureType('pulse')}
                    className={`py-1.5 rounded-lg border font-medium ${
                      measureType === 'pulse' ? 'border-teal-600 bg-teal-50 text-teal-800' : 'border-slate-200'
                    }`}
                  >
                    Heart Rate
                  </button>
                </div>

                {measureType === 'blood_pressure' && (
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      placeholder="Systolic (e.g. 130)"
                      value={measureVal1}
                      onChange={e => setMeasureVal1(e.target.value)}
                      className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                    />
                    <input
                      type="number"
                      placeholder="Diastolic (e.g. 85)"
                      value={measureVal2}
                      onChange={e => setMeasureVal2(e.target.value)}
                      className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                    />
                  </div>
                )}

                {measureType === 'glucose' && (
                  <input
                    type="number"
                    placeholder="Fasting Glucose mg/dL (e.g. 110)"
                    value={measureVal1}
                    onChange={e => setMeasureVal1(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                )}

                {measureType === 'pulse' && (
                  <input
                    type="number"
                    placeholder="Pulse bpm (e.g. 72)"
                    value={measureVal1}
                    onChange={e => setMeasureVal1(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                )}

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={handleAddMeasurementToChat}
                    className="px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-semibold"
                  >
                    Insert Reading into Input
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Input Bar */}
        <div className="p-4 bg-white border-t border-slate-200">
          {/* Staged File Badge (User can review or remove before sending) */}
          {stagedFile && (
            <div className="max-w-4xl mx-auto mb-2 flex items-center justify-between p-2.5 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-900 animate-fadeIn">
              <div className="flex items-center gap-2 truncate">
                <Paperclip className="w-4 h-4 text-teal-600 shrink-0" />
                <span className="font-semibold truncate">{stagedFile.name}</span>
                <span className="text-[10px] text-teal-600 shrink-0">({(stagedFile.size / 1024).toFixed(1)} KB)</span>
              </div>
              <button
                type="button"
                onClick={() => setStagedFile(null)}
                className="p-1 hover:bg-teal-100 rounded-md text-teal-700 transition"
                title="Remove attached file"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <form onSubmit={e => handleSendMessage(e)} className="flex items-center gap-2 max-w-4xl mx-auto">
            <button
              type="button"
              onClick={() => setShowActionDrawer(!showActionDrawer)}
              className="p-2.5 rounded-xl border border-slate-200 hover:bg-teal-50 hover:text-teal-700 text-slate-600 transition"
              title="Add Symptoms or Measurement"
            >
              <Plus className="w-5 h-5" />
            </button>

            {/* Direct File Attachment Clip */}
            <label
              className={`p-2.5 rounded-xl border transition cursor-pointer ${
                stagedFile
                  ? 'bg-teal-50 border-teal-400 text-teal-700'
                  : 'border-slate-200 hover:bg-teal-50 hover:text-teal-700 text-slate-600'
              }`}
              title="Attach Medical Report, Image, PDF, or CSV"
            >
              <Paperclip className="w-5 h-5" />
              <input
                type="file"
                className="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.csv,.tsv,.txt"
                onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setStagedFile(f);
                    e.target.value = '';
                  }
                }}
              />
            </label>

            <input
              type="text"
              value={inputContent}
              onChange={e => setInputContent(e.target.value)}
              placeholder={
                stagedFile
                  ? `File attached (${stagedFile.name}). Type your question or leave blank to analyze and press Send...`
                  : 'Ask your assistant or attach any document/image (PDF, PNG, JPG, CSV)...'
              }
              className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
            />

            <button
              type="submit"
              disabled={sending || (!inputContent.trim() && !stagedFile)}
              className="p-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-sm transition disabled:opacity-50"
              title="Send message and upload staged file"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-[10px] text-center text-slate-400 mt-2">
            Educational Research Assistant · Not a substitute for clinical diagnosis · Emergencies call 112
          </p>
        </div>
      </div>
    </div>
  );
};
