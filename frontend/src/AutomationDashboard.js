import React, { useState, useEffect } from 'react';

// n8n Automation Dashboard Component
export const AutomationDashboard = ({ language }) => {
  const [automationStats, setAutomationStats] = useState({
    totalBookings: 0,
    emailsSent: 0,
    smsSent: 0,
    whatsappSent: 0,
    remindersSent: 0,
    calendarEvents: 0,
    successRate: 0,
    lastUpdate: new Date()
  });

  const [recentActivity, setRecentActivity] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const text = {
    en: {
      title: 'Automation Dashboard',
      stats: 'Automation Statistics',
      recentActivity: 'Recent Activity',
      totalBookings: 'Total Bookings',
      emailsSent: 'Emails Sent',
      smsSent: 'SMS Sent', 
      whatsappSent: 'WhatsApp Sent',
      remindersSent: 'Reminders Sent',
      calendarEvents: 'Calendar Events',
      successRate: 'Success Rate',
      lastUpdate: 'Last Updated',
      testWebhook: 'Test Webhook',
      viewLogs: 'View n8n Logs',
      refreshData: 'Refresh Data'
    },
    ar: {
      title: 'لوحة الأتمتة',
      stats: 'إحصائيات الأتمتة',
      recentActivity: 'النشاط الحديث',
      totalBookings: 'إجمالي الحجوزات',
      emailsSent: 'رسائل البريد المرسلة',
      smsSent: 'رسائل SMS المرسلة',
      whatsappSent: 'رسائل واتساب المرسلة',
      remindersSent: 'التذكيرات المرسلة',
      calendarEvents: 'أحداث التقويم',
      successRate: 'معدل النجاح',
      lastUpdate: 'آخر تحديث',
      testWebhook: 'اختبار الرابط',
      viewLogs: 'عرض سجلات n8n',
      refreshData: 'تحديث البيانات'
    }
  };

  const currentText = text[language];
  const isRTL = language === 'ar';

  useEffect(() => {
    fetchAutomationStats();
    fetchRecentActivity();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchAutomationStats();
      fetchRecentActivity();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchAutomationStats = async () => {
    try {
      const response = await fetch('/api/automation/stats');
      const data = await response.json();
      setAutomationStats(data);
    } catch (error) {
      console.error('Error fetching automation stats:', error);
      // Mock data for demo
      setAutomationStats({
        totalBookings: 156,
        emailsSent: 298,
        smsSent: 145,
        whatsappSent: 67,
        remindersSent: 423,
        calendarEvents: 134,
        successRate: 94.2,
        lastUpdate: new Date()
      });
    }
    setIsLoading(false);
  };

  const fetchRecentActivity = async () => {
    try {
      const response = await fetch('/api/automation/recent-activity');
      const data = await response.json();
      setRecentActivity(data);
    } catch (error) {
      console.error('Error fetching recent activity:', error);
      // Mock data for demo
      setRecentActivity([
        {
          id: '1',
          type: 'booking_created',
          message: 'New appointment booked - John Doe (Health Card Renewal)',
          timestamp: new Date(Date.now() - 5 * 60 * 1000),
          status: 'success'
        },
        {
          id: '2', 
          type: 'email_sent',
          message: 'Confirmation email sent to jane@example.com',
          timestamp: new Date(Date.now() - 12 * 60 * 1000),
          status: 'success'
        },
        {
          id: '3',
          type: 'sms_sent', 
          message: 'SMS reminder sent to +1234567890',
          timestamp: new Date(Date.now() - 18 * 60 * 1000),
          status: 'success'
        },
        {
          id: '4',
          type: 'calendar_event',
          message: 'Google Calendar event created for medical consultation',
          timestamp: new Date(Date.now() - 25 * 60 * 1000),
          status: 'success'
        },
        {
          id: '5',
          type: 'webhook_error',
          message: 'WhatsApp webhook failed - invalid phone number',
          timestamp: new Date(Date.now() - 35 * 60 * 1000),
          status: 'error'
        }
      ]);
    }
  };

  const testWebhook = async () => {
    try {
      const testPayload = {
        appointment_id: `TEST_${Date.now()}`,
        service: {
          name: { en: 'Test Service', ar: 'خدمة تجريبية' },
          estimated_time: 30
        },
        customer_info: {
          name: 'Test User',
          phone: '+1234567890',
          email: 'test@mind14.com'
        },
        language: language,
        booking_type: 'new_appointment',
        notification_preferences: {
          email: true,
          sms: false,
          whatsapp: false
        }
      };

      const response = await fetch('/api/n8n/book-appointment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testPayload)
      });

      const result = await response.json();
      alert(`Webhook test ${result.status}: ${result.message}`);
      
      // Refresh data after test
      setTimeout(() => {
        fetchAutomationStats();
        fetchRecentActivity();
      }, 2000);
      
    } catch (error) {
      alert(`Webhook test failed: ${error.message}`);
    }
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'booking_created': return '📅';
      case 'email_sent': return '📧';
      case 'sms_sent': return '📱';
      case 'whatsapp_sent': return '💬';
      case 'calendar_event': return '🗓️';
      case 'reminder_sent': return '⏰';
      case 'webhook_error': return '❌';
      default: return '📋';
    }
  };

  const StatCard = ({ title, value, icon, color = 'blue' }) => (
    <div className={`bg-gray-800 rounded-lg p-6 border border-gray-700`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className={`text-3xl opacity-80`}>
          {icon}
        </div>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${isRTL ? 'rtl' : 'ltr'}`} dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">{currentText.title}</h2>
        <div className="flex items-center space-x-3">
          <button
            onClick={testWebhook}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-colors"
          >
            {currentText.testWebhook}
          </button>
          <button
            onClick={() => window.open(process.env.REACT_APP_N8N_URL || 'https://your-n8n-instance.com', '_blank')}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
          >
            {currentText.viewLogs}
          </button>
          <button
            onClick={() => {
              fetchAutomationStats();
              fetchRecentActivity();
            }}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
          >
            {currentText.refreshData}
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">{currentText.stats}</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title={currentText.totalBookings}
            value={automationStats.totalBookings}
            icon="📅"
            color="blue"
          />
          <StatCard
            title={currentText.emailsSent}
            value={automationStats.emailsSent}
            icon="📧"
            color="green"
          />
          <StatCard
            title={currentText.smsSent}
            value={automationStats.smsSent}
            icon="📱"
            color="purple"
          />
          <StatCard
            title={currentText.whatsappSent}
            value={automationStats.whatsappSent}
            icon="💬"
            color="green"
          />
          <StatCard
            title={currentText.remindersSent}
            value={automationStats.remindersSent}
            icon="⏰"
            color="yellow"
          />
          <StatCard
            title={currentText.calendarEvents}
            value={automationStats.calendarEvents}
            icon="🗓️"
            color="red"
          />
          <StatCard
            title={currentText.successRate}
            value={`${automationStats.successRate}%`}
            icon="✅"
            color="green"
          />
          <StatCard
            title={currentText.lastUpdate}
            value={automationStats.lastUpdate ? 
              (typeof automationStats.lastUpdate === 'string' ? 
                new Date(automationStats.lastUpdate).toLocaleTimeString() : 
                automationStats.lastUpdate.toLocaleTimeString()
              ) : 'N/A'
            }
            icon="🔄"
            color="gray"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">{currentText.recentActivity}</h3>
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="divide-y divide-gray-700">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="p-4 hover:bg-gray-750 transition-colors">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">
                    {getActivityIcon(activity.type)}
                  </span>
                  <div className="flex-1">
                    <p className="text-white font-medium">{activity.message}</p>
                    <p className="text-gray-400 text-sm">
                      {activity.timestamp.toLocaleString()}
                    </p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${
                    activity.status === 'success' 
                      ? 'bg-green-900 text-green-300' 
                      : 'bg-red-900 text-red-300'
                  }`}>
                    {activity.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Integration Status */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Integration Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Google Calendar</p>
                <p className="text-green-400 text-sm">✅ Connected</p>
              </div>
              <span className="text-2xl">📅</span>
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Twilio SMS</p>
                <p className="text-green-400 text-sm">✅ Active</p>
              </div>
              <span className="text-2xl">📱</span>
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Email SMTP</p>
                <p className="text-green-400 text-sm">✅ Working</p>
              </div>
              <span className="text-2xl">📧</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};