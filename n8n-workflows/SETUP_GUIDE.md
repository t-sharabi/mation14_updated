# MIND14 n8n Workflow Automation - Setup Guide

## 🚀 **Complete Automation System Overview**

This setup provides **comprehensive booking automation** with Email, SMS, WhatsApp notifications, calendar integration, and smart reminder systems.

### **📋 What's Included:**

1. **Main Booking Automation** - Handles new appointments with calendar integration
2. **Multi-Channel Notifications** - Email, SMS, WhatsApp confirmations  
3. **Smart Reminder System** - Automated 24h, 2h, and 30min reminders
4. **Rescheduling Automation** - Handles appointment changes
5. **Cancellation Automation** - Manages appointment cancellations

---

## ⚙️ **Step 1: Environment Variables Setup**

### **Backend Environment (.env)**
Add these variables to your `/app/backend/.env` file:

```bash
# n8n Webhook URLs
N8N_BOOKING_WEBHOOK=https://your-n8n-instance.com/webhook/mind14-booking-webhook
N8N_NOTIFICATION_WEBHOOK=https://your-n8n-instance.com/webhook/mind14-notification-webhook  
N8N_CALENDAR_WEBHOOK=https://your-n8n-instance.com/webhook/mind14-calendar-webhook
N8N_CRM_WEBHOOK=https://your-n8n-instance.com/webhook/mind14-crm-webhook
N8N_RESCHEDULE_WEBHOOK=https://your-n8n-instance.com/webhook/mind14-reschedule-webhook
N8N_CANCELLATION_WEBHOOK=https://your-n8n-instance.com/webhook/mind14-cancellation-webhook

# MIND14 API URL (for n8n to call back)
MIND14_API_URL=https://your-mind14-instance.com
```

### **n8n Environment Variables**
Configure these in your n8n instance:

```bash
# Google Calendar API
GOOGLE_CALENDAR_API_URL=https://www.googleapis.com/calendar/v3

# Email Configuration  
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@mind14.com
SMTP_PASSWORD=your-email-password

# Twilio SMS Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token  
TWILIO_PHONE_NUMBER=+1234567890

# WhatsApp Business API
WHATSAPP_BUSINESS_API_URL=https://graph.facebook.com/v18.0/your-phone-number-id
WHATSAPP_ACCESS_TOKEN=your-whatsapp-access-token

# MIND14 API for callbacks
MIND14_API_URL=https://your-mind14-instance.com
MIND14_API_TOKEN=your-api-token
```

---

## 📥 **Step 2: Import n8n Workflows**

### **Import Method 1: Direct Import**
1. Open your n8n instance
2. Go to **Workflows** → **Import from file**
3. Import each workflow file:
   - `main-booking-automation.json` 
   - `notification-automation.json`
   - `reminder-automation.json`

### **Import Method 2: Copy/Paste**
1. Copy the JSON content from each workflow file
2. In n8n: **Workflows** → **Add workflow** → **Import from clipboard**
3. Paste and save each workflow

---

## 🔗 **Step 3: Integration Setup**

### **A. Google Calendar Integration**
1. **Create Google Cloud Project**: 
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project: "MIND14-Calendar"
   
2. **Enable Calendar API**:
   - APIs & Services → Library → Search "Google Calendar API" → Enable
   
3. **Create OAuth Credentials**:
   - APIs & Services → Credentials → Create Credentials → OAuth 2.0
   - Add redirect URI: `https://your-n8n-instance.com/rest/oauth2-credential/callback`
   
4. **Configure in n8n**:
   - Settings → Credentials → Add → Google Calendar OAuth2 API
   - Enter Client ID and Client Secret

### **B. Twilio SMS Setup**
1. **Create Twilio Account**: [https://www.twilio.com](https://www.twilio.com)
2. **Get Phone Number**: Console → Phone Numbers → Buy a number
3. **Get Credentials**: Console → Account → Account SID & Auth Token
4. **Configure in n8n**: Settings → Credentials → Add → Twilio API

### **C. WhatsApp Business Setup**
1. **Meta Business Account**: [https://business.facebook.com](https://business.facebook.com)
2. **WhatsApp Business API**: Apply for access
3. **Get Access Token**: Meta for Developers → WhatsApp → Configuration
4. **Configure in n8n**: Settings → Credentials → Add → HTTP Header Auth

### **D. Email SMTP Setup**
1. **Gmail Setup** (Recommended):
   - Enable 2-Factor Authentication
   - Generate App Password: Google Account → Security → App passwords
   
2. **Alternative Providers**:
   - **SendGrid**: [https://sendgrid.com](https://sendgrid.com)
   - **Mailgun**: [https://www.mailgun.com](https://www.mailgun.com)
   - **Amazon SES**: [https://aws.amazon.com/ses](https://aws.amazon.com/ses)

---

## 🎯 **Step 4: Workflow Configuration**

### **Webhook URLs**
After importing, your n8n workflows will have these webhook URLs:

```
Main Booking: https://your-n8n.com/webhook/mind14-booking-webhook
Notifications: https://your-n8n.com/webhook/mind14-notification-webhook
Reminders: https://your-n8n.com/webhook/mind14-reminder-webhook
Reschedule: https://your-n8n.com/webhook/mind14-reschedule-webhook
Cancellation: https://your-n8n.com/webhook/mind14-cancellation-webhook
```

### **Activate Workflows**
1. Open each workflow in n8n
2. Click **Activate** toggle (top right)
3. Verify webhook endpoints are active

---

## 🧪 **Step 5: Testing the System**

### **Test Booking Flow**
```bash
# Test booking webhook
curl -X POST "https://your-n8n.com/webhook/mind14-booking-webhook" \
-H "Content-Type: application/json" \
-d '{
  "appointment_id": "TEST123",
  "service": {
    "name": {"en": "Health Card Renewal", "ar": "تجديد البطاقة الصحية"},
    "estimated_time": 30
  },
  "customer_info": {
    "name": "John Doe", 
    "phone": "+1234567890",
    "email": "test@example.com"
  },
  "language": "en",
  "booking_type": "new_appointment",
  "notification_preferences": {
    "email": true,
    "sms": true, 
    "whatsapp": false
  }
}'
```

### **Expected Results**
✅ **Google Calendar Event** created  
✅ **Email confirmation** sent  
✅ **SMS confirmation** sent  
✅ **n8n execution** logged successfully  

---

## 📊 **Step 6: Monitoring & Analytics**

### **n8n Execution Monitoring**
- **Executions**: View all workflow runs
- **Logs**: Check for errors and performance
- **Metrics**: Monitor success rates and timing

### **Integration Health Checks**
```bash
# Check Google Calendar integration
curl -X GET "https://www.googleapis.com/calendar/v3/calendars/primary/events" \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Check Twilio SMS balance  
curl -X GET "https://api.twilio.com/2010-04-01/Accounts/YOUR_SID/Balance.json" \
-u "YOUR_SID:YOUR_AUTH_TOKEN"
```

---

## 🔧 **Advanced Configuration**

### **Custom Message Templates**
Edit the message templates in the notification workflow:

```javascript
// SMS Template (English)
🤖 MIND14: Your appointment is confirmed!

📅 Service: {{ $json.serviceName }}  
🆔 ID: {{ $json.appointmentId }}
⏰ Time: {{ $json.scheduledTime }}

We'll send you reminders. Thank you for choosing MIND14!

// SMS Template (Arabic)  
🤖 MIND14: تم تأكيد موعدك!

📅 الخدمة: {{ $json.serviceName }}
🆔 رقم الموعد: {{ $json.appointmentId }}  
⏰ الوقت: {{ $json.scheduledTime }}

سنرسل لك تذكيرات. شكراً لاختيارك MIND14!
```

### **Reminder Timing Configuration**
Adjust reminder timings in the reminder workflow:

```javascript
// Current: 24h, 2h, 30min before appointment
"reminder_hours_before": [24, 2, 0.5]

// Custom: 48h, 24h, 4h, 1h before
"reminder_hours_before": [48, 24, 4, 1]
```

### **Calendar Integration Options**
- **Google Calendar** ✅ Implemented
- **Outlook Calendar**: Replace Google Calendar node with Microsoft Graph API
- **Apple Calendar**: Use CalDAV integration
- **Custom Calendar**: Implement webhook to your calendar system

---

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Webhook Not Triggering**
   - Check n8n webhook URL is correct
   - Verify workflow is activated
   - Check network connectivity

2. **Email Not Sending**
   - Verify SMTP credentials
   - Check spam folder
   - Test SMTP connection

3. **SMS Not Sending** 
   - Verify Twilio balance
   - Check phone number format (+1234567890)
   - Review Twilio logs

4. **Calendar Event Not Created**
   - Check Google OAuth credentials
   - Verify calendar permissions
   - Test API access

### **Debug Steps**
1. **Check n8n Logs**: Executions → View execution details
2. **Test Individual Nodes**: Right-click → Execute node
3. **Validate Data**: Use Set nodes to inspect data flow
4. **API Testing**: Use HTTP Request nodes to test external APIs

---

## 📚 **Additional Resources**

### **Documentation Links**
- [n8n Documentation](https://docs.n8n.io)
- [Google Calendar API](https://developers.google.com/calendar)
- [Twilio SMS API](https://www.twilio.com/docs/sms)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)

### **Support & Community**
- **n8n Community**: [https://community.n8n.io](https://community.n8n.io)
- **MIND14 Support**: support@mind14.com
- **Documentation**: [Internal MIND14 Docs]

---

## ✅ **Success Checklist**

- [ ] All environment variables configured
- [ ] n8n workflows imported and activated  
- [ ] Google Calendar integration tested
- [ ] Twilio SMS sending successfully
- [ ] Email confirmations working
- [ ] WhatsApp messages (if enabled) sending
- [ ] Reminder system scheduling correctly
- [ ] End-to-end booking flow tested
- [ ] Error handling and logging verified

**🎉 Your MIND14 automation system is now fully operational!**