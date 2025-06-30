import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSpeechSynthesis, useSpeechRecognition } from 'react-speech-kit';

// Voice Integration System for MIND14
// Features: WebRTC, Speech Recognition, Voice Commands, Multilingual Support, Accessibility

// Voice Icons
const VoiceIcons = {
  Mic: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  ),
  MicOff: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 5.586A2 2 0 015 7v6a3 3 0 106 0V9m0 0a3 3 0 113 3m-3-3h3m-3 3v1a7 7 0 01-7-7 7 7 0 0114 0v6m-9 4h.01" />
    </svg>
  ),
  Volume: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M6.343 6.343A8 8 0 004.222 9.879a2.25 2.25 0 001.157 1.157A8 8 0 006.343 17.657l.707-.707M18 12a6 6 0 11-12 0 6 6 0 0112 0z" />
    </svg>
  ),
  VolumeOff: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15.414a2 2 0 001.414.586h4a1 1 0 001-1v-4a1 1 0 00-1-1H7a2 2 0 00-1.414.586l-2.122 2.122a1 1 0 000 1.414l2.122 2.122z" />
    </svg>
  ),
  Settings: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  Play: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15a2 2 0 002-2V6a2 2 0 00-2-2h-1.586a1 1 0 00-.707.293L10.293 6.707A1 1 0 009.586 7H8a2 2 0 00-2 2v4a2 2 0 002 2h1.586z" />
    </svg>
  ),
  Stop: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
    </svg>
  ),
  Language: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
    </svg>
  )
};

// Voice Status Indicator
export const VoiceStatusIndicator = ({ status, language }) => {
  const text = {
    en: {
      listening: 'Listening...',
      processing: 'Processing...',
      idle: 'Ready to listen',
      error: 'Voice error',
      speaking: 'Speaking...'
    },
    ar: {
      listening: 'جاري الاستماع...',
      processing: 'جاري المعالجة...',
      idle: 'جاهز للاستماع',
      error: 'خطأ صوتي',
      speaking: 'جاري التحدث...'
    }
  };

  const currentText = text[language] || text.en;
  const isRTL = language === 'ar';

  const getStatusColor = (status) => {
    switch (status) {
      case 'listening': return 'bg-green-500';
      case 'processing': return 'bg-yellow-500';
      case 'speaking': return 'bg-blue-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className={`flex items-center space-x-2 ${isRTL ? 'flex-row-reverse space-x-reverse' : ''}`}>
      <div className={`w-2 h-2 rounded-full ${getStatusColor(status)} ${status === 'listening' ? 'animate-pulse' : ''}`}></div>
      <span className="text-xs text-gray-400">{currentText[status]}</span>
    </div>
  );
};

// Voice Wave Animation
export const VoiceWaveAnimation = ({ isActive }) => {
  if (!isActive) return null;

  return (
    <div className="flex items-center space-x-1">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="w-1 bg-gradient-to-t from-purple-500 to-pink-500 rounded-full animate-pulse"
          style={{
            height: `${Math.random() * 20 + 10}px`,
            animationDelay: `${i * 0.1}s`,
            animationDuration: '0.5s'
          }}
        />
      ))}
    </div>
  );
};

// Voice Settings Panel
export const VoiceSettings = ({ isOpen, onClose, settings, onSettingsChange, language }) => {
  const isRTL = language === 'ar';
  
  const text = {
    en: {
      title: 'Voice Settings',
      speechLanguage: 'Speech Language',
      voiceSpeed: 'Voice Speed',
      voiceVolume: 'Voice Volume',
      autoSpeak: 'Auto-speak responses',
      continuousListening: 'Continuous listening',
      noiseReduction: 'Noise reduction',
      save: 'Save Settings',
      test: 'Test Voice'
    },
    ar: {
      title: 'إعدادات الصوت',
      speechLanguage: 'لغة الكلام',
      voiceSpeed: 'سرعة الصوت',
      voiceVolume: 'مستوى الصوت',
      autoSpeak: 'تحدث تلقائي للردود',
      continuousListening: 'استماع مستمر',
      noiseReduction: 'تقليل الضوضاء',
      save: 'حفظ الإعدادات',
      test: 'اختبار الصوت'
    }
  };

  const currentText = text[language];

  const voices = [
    { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
    { code: 'en-GB', name: 'English (UK)', flag: '🇬🇧' },
    { code: 'ar-SA', name: 'العربية (السعودية)', flag: '🇸🇦' },
    { code: 'ar-EG', name: 'العربية (مصر)', flag: '🇪🇬' }
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700"
        onClick={(e) => e.stopPropagation()}
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">{currentText.title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          {/* Speech Language */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {currentText.speechLanguage}
            </label>
            <select
              value={settings.speechLanguage}
              onChange={(e) => onSettingsChange({ ...settings, speechLanguage: e.target.value })}
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-purple-500"
            >
              {voices.map((voice) => (
                <option key={voice.code} value={voice.code}>
                  {voice.flag} {voice.name}
                </option>
              ))}
            </select>
          </div>

          {/* Voice Speed */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {currentText.voiceSpeed}: {settings.voiceSpeed}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={settings.voiceSpeed}
              onChange={(e) => onSettingsChange({ ...settings, voiceSpeed: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Voice Volume */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {currentText.voiceVolume}: {Math.round(settings.voiceVolume * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.voiceVolume}
              onChange={(e) => onSettingsChange({ ...settings, voiceVolume: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Toggle Settings */}
          <div className="space-y-3">
            {[
              { key: 'autoSpeak', label: currentText.autoSpeak },
              { key: 'continuousListening', label: currentText.continuousListening },
              { key: 'noiseReduction', label: currentText.noiseReduction }
            ].map((setting) => (
              <div key={setting.key} className="flex items-center justify-between">
                <span className="text-sm text-gray-300">{setting.label}</span>
                <button
                  onClick={() => onSettingsChange({ ...settings, [setting.key]: !settings[setting.key] })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings[setting.key] ? 'bg-purple-600' : 'bg-gray-600'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings[setting.key] ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={() => {
                // Test voice functionality
                const utterance = new SpeechSynthesisUtterance(
                  language === 'ar' ? 'اختبار الصوت يعمل بشكل جيد' : 'Voice test is working correctly'
                );
                utterance.lang = settings.speechLanguage;
                utterance.rate = settings.voiceSpeed;
                utterance.volume = settings.voiceVolume;
                speechSynthesis.speak(utterance);
              }}
              className="flex-1 py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
            >
              {currentText.test}
            </button>
            <button
              onClick={onClose}
              className="flex-1 py-2 px-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg transition-colors text-sm"
            >
              {currentText.save}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Enhanced Speech Recognition Hook
export const useAdvancedSpeechRecognition = ({ 
  language = 'en-US', 
  onResult, 
  onError,
  continuous = false,
  interimResults = true 
}) => {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [confidence, setConfidence] = useState(0);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      setIsSupported(!!SpeechRecognition);

      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        const recognition = recognitionRef.current;

        recognition.continuous = continuous;
        recognition.interimResults = interimResults;
        recognition.lang = language;

        recognition.onstart = () => {
          setIsListening(true);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognition.onresult = (event) => {
          let finalTranscript = '';
          let interimTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result.isFinal) {
              finalTranscript += result[0].transcript;
              setConfidence(result[0].confidence);
            } else {
              interimTranscript += result[0].transcript;
            }
          }

          const fullTranscript = finalTranscript || interimTranscript;
          setTranscript(fullTranscript);
          
          if (onResult && finalTranscript) {
            onResult(finalTranscript, event.results[event.resultIndex][0].confidence);
          }
        };

        recognition.onerror = (event) => {
          setIsListening(false);
          if (onError) {
            onError(event.error);
          }
        };
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [language, continuous, interimResults, onResult, onError]);

  const start = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      setTranscript('');
      setConfidence(0);
      recognitionRef.current.start();
    }
  }, [isListening]);

  const stop = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
  }, [isListening]);

  const toggle = useCallback(() => {
    if (isListening) {
      stop();
    } else {
      start();
    }
  }, [isListening, start, stop]);

  return {
    isSupported,
    isListening,
    transcript,
    confidence,
    start,
    stop,
    toggle
  };
};

// Voice Commands System
export const useVoiceCommands = ({ language, onCommand }) => {
  const commandPatterns = {
    en: {
      newChat: ['new chat', 'start new conversation', 'create chat'],
      sendMessage: ['send', 'send message'],
      clearInput: ['clear', 'clear input', 'delete'],
      openSettings: ['settings', 'open settings', 'voice settings'],
      switchLanguage: ['switch language', 'change language'],
      help: ['help', 'what can you do', 'commands'],
      stopListening: ['stop listening', 'stop', 'silence']
    },
    ar: {
      newChat: ['محادثة جديدة', 'إنشاء محادثة', 'شات جديد'],
      sendMessage: ['إرسال', 'أرسل الرسالة'],
      clearInput: ['مسح', 'حذف النص', 'مسح المدخل'],
      openSettings: ['الإعدادات', 'فتح الإعدادات', 'إعدادات الصوت'],
      switchLanguage: ['تغيير اللغة', 'بدل اللغة'],
      help: ['مساعدة', 'ماذا تستطيع أن تفعل', 'الأوامر'],
      stopListening: ['توقف عن الاستماع', 'توقف', 'صمت']
    }
  };

  const parseCommand = useCallback((transcript) => {
    const patterns = commandPatterns[language] || commandPatterns.en;
    const normalizedTranscript = transcript.toLowerCase().trim();

    for (const [command, variations] of Object.entries(patterns)) {
      for (const variation of variations) {
        if (normalizedTranscript.includes(variation.toLowerCase())) {
          return command;
        }
      }
    }

    return null;
  }, [language]);

  const processVoiceInput = useCallback((transcript, confidence) => {
    const command = parseCommand(transcript);
    
    if (command && confidence > 0.7) {
      onCommand(command, transcript);
      return true;
    }
    
    return false;
  }, [parseCommand, onCommand]);

  return { processVoiceInput, parseCommand };
};

// Main Voice Control Component
export const VoiceControl = ({ 
  onSendMessage, 
  onNewChat, 
  language = 'en', 
  isVisible = true,
  className = ""
}) => {
  const [voiceSettings, setVoiceSettings] = useState({
    speechLanguage: language === 'ar' ? 'ar-SA' : 'en-US',
    voiceSpeed: 1,
    voiceVolume: 0.8,
    autoSpeak: true,
    continuousListening: false,
    noiseReduction: true
  });

  const [showSettings, setShowSettings] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('idle');
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [voiceError, setVoiceError] = useState(null);

  const isRTL = language === 'ar';

  // Text-to-Speech
  const { speak, cancel, speaking } = useSpeechSynthesis({
    onEnd: () => setVoiceStatus('idle')
  });

  // Voice Commands
  const { processVoiceInput } = useVoiceCommands({
    language,
    onCommand: (command, transcript) => {
      switch (command) {
        case 'newChat':
          onNewChat();
          break;
        case 'sendMessage':
          if (currentTranscript.trim()) {
            onSendMessage(currentTranscript);
            setCurrentTranscript('');
          }
          break;
        case 'clearInput':
          setCurrentTranscript('');
          break;
        case 'openSettings':
          setShowSettings(true);
          break;
        case 'help':
          const helpText = language === 'ar' 
            ? 'يمكنك قول: محادثة جديدة، إرسال، مسح، الإعدادات'
            : 'You can say: new chat, send, clear, settings';
          speak({ text: helpText, voice: { lang: voiceSettings.speechLanguage } });
          break;
        case 'stopListening':
          stop();
          break;
      }
    }
  });

  // Speech Recognition
  const {
    isSupported,
    isListening,
    transcript,
    confidence,
    start,
    stop,
    toggle
  } = useAdvancedSpeechRecognition({
    language: voiceSettings.speechLanguage,
    continuous: voiceSettings.continuousListening,
    onResult: (finalTranscript, confidence) => {
      setVoiceStatus('processing');
      
      // Check for voice commands first
      const isCommand = processVoiceInput(finalTranscript, confidence);
      
      if (!isCommand) {
        // Regular message input
        setCurrentTranscript(finalTranscript);
        
        // Auto-send if confidence is high and auto-speak is enabled
        if (confidence > 0.8 && voiceSettings.autoSpeak) {
          setTimeout(() => {
            onSendMessage(finalTranscript);
            setCurrentTranscript('');
          }, 1000);
        }
      }
      
      setVoiceStatus('idle');
    },
    onError: (error) => {
      setVoiceStatus('error');
      setVoiceError(error);
      console.error('Speech recognition error:', error);
    }
  });

  // Update voice status based on states
  useEffect(() => {
    if (speaking) {
      setVoiceStatus('speaking');
    } else if (isListening) {
      setVoiceStatus('listening');
    } else {
      setVoiceStatus('idle');
    }
  }, [speaking, isListening]);

  // Auto-speak responses if enabled
  const speakResponse = (text) => {
    if (voiceSettings.autoSpeak && text) {
      speak({
        text,
        voice: { lang: voiceSettings.speechLanguage },
        rate: voiceSettings.voiceSpeed,
        volume: voiceSettings.voiceVolume
      });
    }
  };

  if (!isVisible || !isSupported) {
    return null;
  }

  const text = {
    en: {
      startListening: 'Start voice input',
      stopListening: 'Stop voice input',
      voiceSettings: 'Voice settings',
      speakLastMessage: 'Speak last message',
      unsupported: 'Voice not supported in this browser'
    },
    ar: {
      startListening: 'بدء الإدخال الصوتي',
      stopListening: 'إيقاف الإدخال الصوتي',
      voiceSettings: 'إعدادات الصوت',
      speakLastMessage: 'تحدث بآخر رسالة',
      unsupported: 'الصوت غير مدعوم في هذا المتصفح'
    }
  };

  const currentText = text[language];

  return (
    <div className={`voice-control-container ${className}`} dir={isRTL ? 'rtl' : 'ltr'}>
      <div className={`flex items-center space-x-2 ${isRTL ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* Main Voice Button */}
        <button
          onClick={toggle}
          className={`p-3 rounded-full transition-all duration-200 transform hover:scale-105 ${
            isListening
              ? 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg'
              : voiceStatus === 'error'
              ? 'bg-gradient-to-r from-red-500 to-red-600 text-white'
              : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white'
          }`}
          title={isListening ? currentText.stopListening : currentText.startListening}
        >
          {isListening ? (
            <VoiceIcons.MicOff className="w-5 h-5" />
          ) : (
            <VoiceIcons.Mic className="w-5 h-5" />
          )}
        </button>

        {/* Voice Wave Animation */}
        <VoiceWaveAnimation isActive={isListening} />

        {/* Speak Button */}
        <button
          onClick={() => {
            if (speaking) {
              cancel();
            } else {
              const lastMessage = currentTranscript || 'Hello, I am MIND14 virtual assistant.';
              speakResponse(lastMessage);
            }
          }}
          className="p-2 text-gray-400 hover:text-purple-400 hover:bg-gray-700 rounded-lg transition-colors"
          title={currentText.speakLastMessage}
        >
          {speaking ? (
            <VoiceIcons.Stop className="w-4 h-4" />
          ) : (
            <VoiceIcons.Volume className="w-4 h-4" />
          )}
        </button>

        {/* Settings Button */}
        <button
          onClick={() => setShowSettings(true)}
          className="p-2 text-gray-400 hover:text-purple-400 hover:bg-gray-700 rounded-lg transition-colors"
          title={currentText.voiceSettings}
        >
          <VoiceIcons.Settings className="w-4 h-4" />
        </button>
      </div>

      {/* Voice Status */}
      <div className="mt-2">
        <VoiceStatusIndicator status={voiceStatus} language={language} />
      </div>

      {/* Current Transcript Display */}
      {currentTranscript && (
        <div className="mt-2 p-2 bg-gray-800 rounded-lg border border-gray-700">
          <p className="text-sm text-gray-300">{currentTranscript}</p>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-500">
              {language === 'ar' ? 'مستوى الثقة' : 'Confidence'}: {Math.round(confidence * 100)}%
            </span>
            <button
              onClick={() => {
                onSendMessage(currentTranscript);
                setCurrentTranscript('');
              }}
              className="text-xs text-purple-400 hover:text-purple-300"
            >
              {language === 'ar' ? 'إرسال' : 'Send'}
            </button>
          </div>
        </div>
      )}

      {/* Voice Settings Panel */}
      <VoiceSettings
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={voiceSettings}
        onSettingsChange={setVoiceSettings}
        language={language}
      />

      {/* Error Display */}
      {voiceError && (
        <div className="mt-2 p-2 bg-red-900 border border-red-700 rounded-lg">
          <p className="text-sm text-red-300">
            {language === 'ar' ? 'خطأ في الصوت' : 'Voice Error'}: {voiceError}
          </p>
        </div>
      )}
    </div>
  );
};

// Voice Accessibility Features
export const VoiceAccessibility = ({ message, language, isEnabled }) => {
  const { speak } = useSpeechSynthesis();

  useEffect(() => {
    if (isEnabled && message && message.role === 'assistant') {
      const voiceLang = language === 'ar' ? 'ar-SA' : 'en-US';
      speak({
        text: message.content,
        voice: { lang: voiceLang }
      });
    }
  }, [message, language, isEnabled, speak]);

  return null;
};

export default VoiceControl;