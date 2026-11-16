import React from 'react';
import { 
  Home,
  FileText,
  Bot,
  Users,
  Sparkles,
  MapPin,
  Settings,
  FolderHeart,
  BarChart3,
  LogOut, 
  Menu, 
  X, 
  ShieldAlert,
  ChevronRight,
  User as UserIcon,
  HeartPulse,
  Building2,
  Stethoscope,
  Receipt
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Layout: React.FC<LayoutProps> = ({ children, activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const navigationItems = [
    { id: 'home', label: 'Home Dashboard', icon: Home, roles: ['patient', 'doctor', 'nurse', 'hospital_admin', 'admin', 'public_health_analyst'] },
    // HMS 4 Integrated Dashboards & Stations
    { id: 'management', label: 'Management & BI', icon: Building2, roles: ['hospital_admin', 'admin'] },
    { id: 'doctor_portal', label: 'Doctor Station', icon: Stethoscope, roles: ['doctor', 'hospital_admin', 'admin'] },
    { id: 'nurse_portal', label: 'Nurse Station', icon: HeartPulse, roles: ['nurse', 'hospital_admin', 'admin'] },
    { id: 'billing', label: 'Billing & Invoices', icon: Receipt, roles: ['patient', 'hospital_admin', 'admin'] },
    // Patient EHR & Health Record
    { id: 'health_record', label: 'My Health Record', icon: FileText, roles: ['patient', 'doctor', 'nurse', 'hospital_admin', 'admin'] },
    { id: 'assistant', label: 'AI Health Assistant', icon: Bot, roles: ['patient', 'doctor', 'nurse', 'hospital_admin', 'admin'] },
    { id: 'family_history', label: 'Family Accounts & Care', icon: Users, roles: ['patient', 'doctor', 'admin'] },
    { id: 'daily_tracking', label: 'Daily Health Tracking', icon: HeartPulse, roles: ['patient', 'doctor', 'admin'] },
    { id: 'future_insights', label: 'Future Health Insights', icon: Sparkles, roles: ['patient', 'doctor', 'admin'] },
    { id: 'nearby_care', label: 'Find Nearby Care', icon: MapPin, roles: ['patient', 'doctor', 'admin'] },
    { id: 'settings', label: 'Settings & Profile', icon: Settings, roles: ['patient', 'doctor', 'nurse', 'hospital_admin', 'admin', 'public_health_analyst'] },
    // Provider views for clinicians/analysts
    { id: 'patients', label: 'Clinical Directory', icon: FolderHeart, roles: ['doctor', 'hospital_admin', 'admin'] },
    { id: 'analytics', label: 'Public Health Analytics', icon: BarChart3, roles: ['admin', 'public_health_analyst', 'doctor', 'hospital_admin'] },
  ];

  const filteredNav = navigationItems.filter(item => 
    !user || item.roles.includes(user.role)
  );

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar for Desktop */}
      <aside className="hidden md:flex md:w-64 md:flex-col bg-white border-r border-slate-200 shadow-sm">
        {/* Brand Logo & Header */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-100">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-teal-600 text-white shadow-md shadow-teal-600/20">
            <span className="font-bold text-xl leading-none">आ</span>
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-tight">Aarogya Drishti</h1>
            <p className="text-[11px] font-medium text-teal-600 tracking-wide uppercase">AI Health Companion</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {filteredNav.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-teal-50 text-teal-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-teal-600" />}
              </button>
            );
          })}
        </nav>

        {/* User Card & Logout */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-teal-100 text-teal-800 font-semibold flex items-center justify-center text-xs">
              {user?.full_name ? user.full_name.charAt(0) : <UserIcon className="w-4 h-4" />}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-slate-900 truncate">{user?.full_name || 'Patient'}</p>
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider truncate">
                {user?.role === 'patient' && user.patient_id ? `${user.patient_id}` : user?.role}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-lg transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <span className="text-sm font-semibold text-slate-800">
              {filteredNav.find(i => i.id === activeTab)?.label || 'Overview'}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200/60">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Research Proof-of-Concept · Not a Diagnostic Device</span>
            </span>
            <div className="text-xs text-slate-500 hidden lg:block">
              Connected: <span className="font-semibold text-teal-700">{user?.full_name}</span>
            </div>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-b border-slate-200 px-4 py-3 space-y-1 shadow-lg">
            {filteredNav.map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                    isActive ? 'bg-teal-50 text-teal-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
            <div className="pt-2 border-t border-slate-100 flex justify-between items-center">
              <span className="text-xs text-slate-500">{user?.full_name}</span>
              <button
                onClick={logout}
                className="text-xs font-medium text-rose-600 hover:underline"
              >
                Sign Out
              </button>
            </div>
          </div>
        )}

        {/* Dynamic Page Body */}
        <main className="flex-1 overflow-y-auto bg-slate-50">
          {children}
        </main>
      </div>
    </div>
  );
};
