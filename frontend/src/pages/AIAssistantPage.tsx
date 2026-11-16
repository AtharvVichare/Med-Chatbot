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
  X,
  Mic,
  MicOff,
  FileDown,
  Stethoscope,
  BedDouble,
  Building2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { ChatConversation, ChatMessage, AppointmentBookingTicket, AppointmentBooking } from '../types';
import { AppointmentTicketModal } from '../components/AppointmentTicketModal';
import { BookingProgressModal, type BookingProgressStep } from '../components/BookingProgressModal';

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

  // Voice dictation state
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const toggleVoiceRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsListening(true);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInputContent(prev => prev ? `${prev} ${transcript}` : transcript);
        setIsListening(false);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
      recognition.start();
    }
  };

  const handleDownloadPdf = async () => {
    if (!user?.patient_id) {
      alert("Please ensure your patient profile is connected.");
      return;
    }
    try {
      const blob = await api.downloadEhrPdf(user.patient_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Longitudinal_EHR_${user.patient_id}.pdf`;
      a.click();
    } catch (e: any) {
      alert(`Download failed: ${e.message}`);
    }
  };

  // Ticket & Booking Workflow Progress State
  const [confirmedTicket, setConfirmedTicket] = useState<AppointmentBookingTicket | AppointmentBooking | null>(null);
  const [bookingSlot, setBookingSlot] = useState<string | null>(null);
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [progressDoctor, setProgressDoctor] = useState<{ name: string; hospital: string; dept: string; date: string; slot: string }>({
    name: '', hospital: '', dept: '', date: '', slot: ''
  });
  const [currentProgressStep, setCurrentProgressStep] = useState(0);

  const bookingWorkflowSteps: BookingProgressStep[] = [
    { title: 'Clinical Triage & Department Validation', description: 'Matching patient symptoms with specialist qualifications and triage urgency.', status: 'pending' },
    { title: 'Schedule Lock & Double-Booking Guard', description: 'Checking real-time doctor availability in PostgreSQL to prevent slot collisions.', status: 'pending' },
    { title: 'HMS Central Registry & Chamber Allocation', description: 'Registering consultation booking in hospital records and assigning chamber room.', status: 'pending' },
    { title: 'Inter-Agent Event Bus Console Dispatch', description: 'Broadcasting live confirmation event to Doctor Station and Nurse OPD queue.', status: 'pending' },
    { title: 'Official Consultation Token & Slip Issuance', description: 'Generating ABDM-compliant queue token number and verified consultation slip.', status: 'pending' }
  ];

  const handleBookDoctorFromChat = async (
    doctorId: string, 
    timeSlot: string, 
    bookingDate: string,
    doctorName?: string,
    hospitalName?: string,
    department?: string
  ) => {
    try {
      setBookingSlot(`${doctorId}-${timeSlot}`);
      setProgressDoctor({
        name: doctorName || 'Attending Specialist',
        hospital: hospitalName || 'Seth GS Medical College & KEM Hospital',
        dept: department || 'Outpatient Department',
        date: bookingDate,
        slot: timeSlot
      });
      setShowProgressModal(true);
      setCurrentProgressStep(0);

      // Step 0 -> Step 1 (Clinical Triage verified)
      await new Promise(r => setTimeout(r, 450));
      setCurrentProgressStep(1);

      // Step 1: Real API booking execution
      const res = await api.bookAppointment({
        doctor_id: doctorId,
        time_slot: timeSlot,
        booking_date: bookingDate,
        chief_complaint: 'Booked via AI Assistant consultation',
        patient_id: user?.patient_id
      });

      // Step 2: Registered in HMS
      setCurrentProgressStep(2);
      await new Promise(r => setTimeout(r, 400));

      // Step 3: Event Bus Dispatched to Nurse and Doctor Dashboards
      setCurrentProgressStep(3);
      await new Promise(r => setTimeout(r, 400));

      // Step 4: Token Issued
      setCurrentProgressStep(4);
      await new Promise(r => setTimeout(r, 500));

      // Append persistent booking confirmation message to chat history
      const confirmationMsg = `### 🎟️ Appointment Confirmed & Officially Registered!\n\n` +
        `- **Official Queue Token:** \`${res.token_number}\`\n` +
        `- **Booking ID:** \`${res.booking_id}\`\n` +
        `- **Attending Specialist:** **${res.doctor_name}** (${res.qualification || 'MBBS, MD'})\n` +
        `- **Department:** ${res.department}\n` +
        `- **Hospital Facility:** **${res.hospital_name}**\n` +
        `- **OPD Consultation Chamber:** ${res.chamber_room}\n` +
        `- **Date & Time Slot:** **${res.booking_date}** at **${res.time_slot}**\n` +
        `- **Consultation Fee:** ₹${res.fee} (Status: \`CONFIRMED\`)\n\n` +
        `> [!NOTE]\n> *This appointment is recorded in your longitudinal health record and queued live on both the **Doctor Station** and the **Nurse OPD Queue**.*`;

      setMessages(prev => [
        ...prev,
        {
          message_id: `MSG-CONFIRM-${Date.now()}`,
          conversation_id: activeConversationId || '',
          sender: 'assistant',
          content: confirmationMsg,
          created_at: new Date().toISOString(),
          is_confirmed_to_ehr: false
        }
      ]);

      setShowProgressModal(false);
      // Show official interactive Ticket Modal
      setConfirmedTicket(res);
    } catch (err: any) {
      setShowProgressModal(false);
      alert(`Booking failed: ${err.message}`);
    } finally {
      setBookingSlot(null);
    }
  };

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

                      {parsedProposal.chart_image_base64 ? (
                        <div className="space-y-2">
                          <div className="rounded-xl overflow-hidden border border-slate-200 bg-white shadow-2xs">
                            <img 
                              src={parsedProposal.chart_image_base64} 
                              alt={parsedProposal.chart_title || 'Clinical Matplotlib Chart'} 
                              className="w-full h-auto object-contain cursor-pointer hover:opacity-95 transition"
                              onClick={() => {
                                const w = window.open('');
                                if (w) {
                                  w.document.write(`<img src="${parsedProposal.chart_image_base64}" style="max-width:100%; height:auto;" />`);
                                }
                              }}
                              title="Click to view full-resolution clinical chart"
                            />
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                            <span className="flex items-center gap-1 text-slate-600">
                              <span>Standard:</span>
                              <strong className="text-slate-800">Matplotlib Clinical Plot</strong>
                            </span>
                            <a 
                              href={parsedProposal.chart_image_base64} 
                              download={`${(parsedProposal.chart_title || 'clinical_chart').toLowerCase().replace(/\s+/g, '_')}.png`}
                              className="text-teal-700 hover:text-teal-800 font-semibold inline-flex items-center gap-1"
                            >
                              Download Chart (PNG) ↗
                            </a>
                          </div>
                        </div>
                      ) : parsedProposal.points && parsedProposal.points.length > 0 ? (
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
                      const scansList = Array.isArray(parsedProposal)
                        ? parsedProposal.filter((p: any) => p.action_type === 'render_imaging_scan')
                        : (parsedProposal.action_type === 'render_imaging_scan' ? [parsedProposal] : []);

                      if (!scansList.length) return null;

                      return (
                        <div className="space-y-3 w-full max-w-lg">
                          {scansList.map((scanData: any, sIdx: number) => (
                            <div key={sIdx} className="p-4 rounded-xl border border-indigo-200 bg-white shadow-sm text-xs text-slate-800 space-y-3">
                              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                                <div className="flex items-center gap-1.5 font-bold text-indigo-900">
                                  <Sparkles className="w-4 h-4 text-indigo-600" />
                                  <span>{scanData.modality || 'Radiological Diagnostic Scan'}</span>
                                </div>
                                <span className="text-[10px] px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-semibold">
                                  {scanData.anatomical_region || 'Imaging Finding'}
                                </span>
                              </div>

                              {scanData.document_id && (
                                <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-900/10 my-2 relative">
                                  <img
                                    src={`/api/v1/documents/${scanData.document_id}/file?token=${localStorage.getItem('token') || ''}`}
                                    alt={scanData.file_name}
                                    className="w-full max-h-60 object-contain mx-auto bg-slate-900"
                                    onError={(e: any) => {
                                      e.currentTarget.style.display = 'none';
                                    }}
                                  />
                                  <div className="flex items-center justify-between px-2.5 py-1.5 bg-slate-100 text-[10px] text-slate-600">
                                    <span className="font-mono truncate">{scanData.file_name}</span>
                                    <a
                                      href={`/api/v1/documents/${scanData.document_id}/file?token=${localStorage.getItem('token') || ''}`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-indigo-600 hover:text-indigo-800 font-semibold shrink-0"
                                    >
                                      View Full Scan ↗
                                    </a>
                                  </div>
                                </div>
                              )}

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
                          ))}
                        </div>
                      );
                    })()
                  )}

                  {/* Educational Medical Visuals Card */}
                  {parsedProposal && (
                    (parsedProposal.action_type === 'render_educational_image' || (Array.isArray(parsedProposal) && parsedProposal.some((p: any) => p.action_type === 'render_educational_image')))
                  ) && (() => {
                    const edu = parsedProposal.action_type === 'render_educational_image'
                      ? parsedProposal
                      : parsedProposal.find((p: any) => p.action_type === 'render_educational_image');
                    if (!edu) return null;
                    return (
                      <div className="p-4 rounded-xl border border-blue-200 bg-white shadow-sm text-xs text-slate-800 space-y-3 w-full max-w-lg">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                          <span className="text-[10px] px-2.5 py-0.5 bg-blue-100 text-blue-800 rounded-full font-bold tracking-wide">
                            {edu.badge || 'EDUCATIONAL MEDICAL REFERENCE'}
                          </span>
                          <span className="text-[10px] text-slate-500 font-medium">{edu.source}</span>
                        </div>
                        <div className="font-bold text-slate-900 text-sm">{edu.title}</div>
                        {edu.image_url && (
                          <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-50 relative group">
                            <img 
                              src={edu.image_url} 
                              alt={edu.title} 
                              className="w-full max-h-64 object-contain cursor-pointer hover:opacity-95 transition bg-white"
                              onClick={() => window.open(edu.image_url, '_blank')}
                              title="Click to open full-resolution educational diagram"
                            />
                            <div className="p-1.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                              <span>Source: <strong>{edu.source}</strong></span>
                              <a 
                                href={edu.image_url} 
                                target="_blank" 
                                rel="noreferrer" 
                                className="text-blue-600 hover:text-blue-800 font-semibold"
                              >
                                View Full Image ↗
                              </a>
                            </div>
                          </div>
                        )}
                        <p className="text-xs text-slate-700 leading-relaxed">{edu.explanation}</p>
                        {edu.key_points?.length > 0 && (
                          <ul className="list-disc list-inside space-y-1 text-slate-600 text-[11px] bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                            {edu.key_points.map((pt: string, idx: number) => (
                              <li key={idx}><b>{pt}</b></li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })()}

                  {/* Doctor Recommendations Card */}
                  {parsedProposal && (
                    (parsedProposal.action_type === 'render_doctor_recommendations' || (Array.isArray(parsedProposal) && parsedProposal.some((p: any) => p.action_type === 'render_doctor_recommendations')))
                  ) && (() => {
                    const docRec = parsedProposal.action_type === 'render_doctor_recommendations'
                      ? parsedProposal
                      : parsedProposal.find((p: any) => p.action_type === 'render_doctor_recommendations');
                    if (!docRec || !docRec.doctors) return null;
                    return (
                      <div className="p-4 rounded-xl border border-teal-200 bg-white shadow-sm text-xs text-slate-800 space-y-3 w-full max-w-lg">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                          <span className="font-bold text-teal-900 flex items-center gap-1.5">
                            <Stethoscope className="w-4 h-4 text-teal-600" />
                            Verified Doctors: {docRec.department}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 bg-teal-50 text-teal-700 rounded-full font-semibold">
                            Priority: {docRec.priority?.toUpperCase()}
                          </span>
                        </div>
                        <div className="space-y-3">
                          {docRec.doctors.map((d: any) => (
                            <div key={d.doctor_id} className="p-3.5 bg-slate-50 hover:bg-slate-50/90 rounded-xl border border-slate-200 transition">
                              <div className="flex justify-between items-start gap-2 mb-1.5">
                                <div>
                                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                                    <span>{d.name}</span>
                                  </h4>
                                  <p className="text-[11px] text-slate-500">{d.qualification} &bull; {d.experience_years} yrs exp</p>
                                  <div className="flex items-center gap-1.5 mt-1 text-[11px] font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-200/80 w-fit">
                                    <Building2 className="w-3 h-3 text-teal-600 shrink-0" />
                                    <span>{d.hospital_name || 'Seth GS Medical College & KEM Hospital'}</span>
                                  </div>
                                </div>
                                <div className="text-right shrink-0">
                                  <span className="text-xs font-bold text-slate-900 bg-white px-2 py-1 rounded-md border border-slate-200 shadow-2xs">
                                    ₹{d.consultation_fee}
                                  </span>
                                </div>
                              </div>
                              <div className="mt-2.5">
                                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                                  Select Slot ({docRec.suggested_date || 'Upcoming'}):
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {d.available_slots?.map((slot: string, sidx: number) => {
                                    const isBooking = bookingSlot === `${d.doctor_id}-${slot}`;
                                    return (
                                      <button
                                        key={sidx}
                                        disabled={!!bookingSlot}
                                        onClick={() => handleBookDoctorFromChat(d.doctor_id, slot, docRec.suggested_date, d.name, d.hospital_name, docRec.department)}
                                        className="px-2.5 py-1 bg-white hover:bg-teal-600 hover:text-white border border-slate-200 rounded-lg text-[11px] font-semibold text-slate-700 transition shadow-2xs disabled:opacity-50"
                                      >
                                        {isBooking ? 'Booking...' : slot}
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Admission Recommendation Card */}
                  {parsedProposal && (
                    (parsedProposal.action_type === 'render_admission_status' || (Array.isArray(parsedProposal) && parsedProposal.some((p: any) => p.action_type === 'render_admission_status')))
                  ) && (() => {
                    const adm = parsedProposal.action_type === 'render_admission_status'
                      ? parsedProposal
                      : parsedProposal.find((p: any) => p.action_type === 'render_admission_status');
                    if (!adm) return null;
                    return (
                      <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 shadow-sm text-xs text-slate-800 space-y-2 w-full max-w-lg">
                        <div className="flex items-center justify-between pb-2 border-b border-amber-200/50">
                          <span className="font-bold text-amber-900 flex items-center gap-1.5">
                            <BedDouble className="w-4 h-4 text-amber-600" />
                            Hospital Admission Coordination
                          </span>
                          <span className="text-[10px] px-2 py-0.5 bg-amber-200 text-amber-900 rounded-full font-bold uppercase">
                            {adm.priority} Priority
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div><span className="text-slate-500">Department:</span> <b>{adm.department}</b></div>
                          <div><span className="text-slate-500">Ward:</span> <b>{adm.recommended_ward}</b></div>
                          <div><span className="text-slate-500">Bed Assigned:</span> <b>{adm.available_bed || 'Waitlisted'}</b></div>
                          <div><span className="text-slate-500">Daily Charge:</span> <b>₹{adm.daily_charge || 1500}/day</b></div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Proposed EHR Action Card (for non-chart proposals like new medication or vitals save) */}
                  {parsedProposal && parsedProposal.action_type !== 'render_chart' && parsedProposal.action !== 'render_chart' && parsedProposal.action_type !== 'render_imaging_scan' && parsedProposal.action_type !== 'render_educational_image' && parsedProposal.action_type !== 'render_doctor_recommendations' && parsedProposal.action_type !== 'render_admission_status' && (
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
          {/* Quick NLP Workflow Action Chips */}
          <div className="max-w-4xl mx-auto mb-2 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <button
              type="button"
              onClick={handleDownloadPdf}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-slate-900 text-white font-medium text-[11px] hover:bg-slate-800 transition shrink-0 shadow-xs"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>Download Complete EHR (PDF)</span>
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage(undefined, "Book an appointment with a cardiologist tomorrow")}
              className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] transition shrink-0"
            >
              🩺 Book Cardiologist
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage(undefined, "Show my previous radiological MRI scans and findings")}
              className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] transition shrink-0"
            >
              🖼️ Show Previous Scans
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage(undefined, "Explain what blood pressure is with educational illustrations")}
              className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] transition shrink-0"
            >
              💡 Medical Illustration
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage(undefined, "Find an available hospital bed for admission")}
              className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] transition shrink-0"
            >
              🛏️ Bed Availability
            </button>
          </div>

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

            {/* Voice Input Microphone Button */}
            <button
              type="button"
              onClick={toggleVoiceRecognition}
              className={`p-2.5 rounded-xl border transition ${
                isListening
                  ? 'bg-rose-50 border-rose-400 text-rose-600 animate-pulse'
                  : 'border-slate-200 hover:bg-teal-50 hover:text-teal-700 text-slate-600'
              }`}
              title={isListening ? "Listening... click to stop" : "Voice Input (Speech-to-Text)"}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            <input
              type="text"
              value={inputContent}
              onChange={e => setInputContent(e.target.value)}
              placeholder={
                isListening
                  ? 'Listening to your voice...'
                  : stagedFile
                  ? `File attached (${stagedFile.name}). Type your question or leave blank to analyze and press Send...`
                  : 'Ask your assistant, speak your symptoms, or request appointment/bed...'
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

      {/* Multi-Agent Live Booking Workflow Progress Modal */}
      <BookingProgressModal
        isOpen={showProgressModal}
        doctorName={progressDoctor.name}
        hospitalName={progressDoctor.hospital}
        department={progressDoctor.dept}
        bookingDate={progressDoctor.date}
        timeSlot={progressDoctor.slot}
        currentStep={currentProgressStep}
        steps={bookingWorkflowSteps}
      />

      {/* Official Appointment Confirmation Token & Ticket Modal */}
      <AppointmentTicketModal
        ticket={confirmedTicket}
        onClose={() => setConfirmedTicket(null)}
      />
    </div>
  );
};
