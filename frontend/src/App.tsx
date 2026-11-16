import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { LoginPage } from './pages/LoginPage';
import { HomePage } from './pages/HomePage';
import { MyHealthRecordPage } from './pages/MyHealthRecordPage';
import { AIAssistantPage } from './pages/AIAssistantPage';
import { FamilyHistoryPage } from './pages/FamilyHistoryPage';
import { DailyTrackingPage } from './pages/DailyTrackingPage';
import { FutureInsightsPage } from './pages/FutureInsightsPage';
import { FindNearbyCarePage } from './pages/FindNearbyCarePage';
import { SettingsPage } from './pages/SettingsPage';
import { PatientManagementPage } from './pages/PatientManagementPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SymptomAnalysisPage } from './pages/SymptomAnalysisPage';
import { MedicalKnowledgePage } from './pages/MedicalKnowledgePage';
import { ManagementDashboardPage } from './pages/ManagementDashboardPage';
import { DoctorDashboardPage } from './pages/DoctorDashboardPage';
import { NurseDashboardPage } from './pages/NurseDashboardPage';
import { BillingPage } from './pages/BillingPage';
import { CompleteProfileModal } from './components/CompleteProfileModal';

const AppContent: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  
  const getDefaultTab = (role?: string) => {
    if (role === 'doctor') return 'doctor_portal';
    if (role === 'nurse') return 'nurse_portal';
    if (role === 'hospital_admin') return 'management';
    if (role === 'public_health_analyst') return 'analytics';
    return 'home';
  };

  const [activeTab, setActiveTab] = useState<string>(() => getDefaultTab(user?.role));
  const [showCompleteProfile, setShowCompleteProfile] = useState<boolean>(false);

  React.useEffect(() => {
    if (user?.role) {
      setActiveTab(getDefaultTab(user.role));
    }
    // If patient user is logged in and their gender is missing or unspecified, prompt onboarding
    if (user?.role === 'patient' && (!user.gender || user.gender === 'unspecified')) {
      setShowCompleteProfile(true);
    }
  }, [user]);

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const renderActiveView = () => {
    switch (activeTab) {
      case 'home':
      case 'dashboard':
        return <HomePage onNavigate={setActiveTab} />;
      case 'management':
        return <ManagementDashboardPage />;
      case 'doctor_portal':
        return <DoctorDashboardPage />;
      case 'nurse_portal':
        return <NurseDashboardPage />;
      case 'billing':
        return <BillingPage />;
      case 'health_record':
        return <MyHealthRecordPage />;
      case 'assistant':
        return <AIAssistantPage />;
      case 'family_history':
        return <FamilyHistoryPage />;
      case 'daily_tracking':
        return <DailyTrackingPage />;
      case 'future_insights':
        return <FutureInsightsPage />;
      case 'nearby_care':
        return <FindNearbyCarePage />;
      case 'settings':
        return <SettingsPage />;
      case 'patients':
        return <PatientManagementPage />;
      case 'analytics':
        return <AnalyticsPage />;
      case 'prediction':
        return <SymptomAnalysisPage />;
      case 'knowledge':
        return <MedicalKnowledgePage />;
      default:
        return <HomePage onNavigate={setActiveTab} />;
    }
  };

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {renderActiveView()}
      <CompleteProfileModal
        isOpen={showCompleteProfile}
        onClose={() => setShowCompleteProfile(false)}
      />
    </Layout>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
