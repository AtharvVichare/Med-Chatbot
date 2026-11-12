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

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<string>('home');

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const renderActiveView = () => {
    switch (activeTab) {
      case 'home':
      case 'dashboard':
        return <HomePage onNavigate={setActiveTab} />;
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
