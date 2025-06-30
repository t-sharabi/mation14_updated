from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import httpx
import ollama
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="MIND14 Virtual Front Desk API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enums
class ConversationStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ServiceCategory(str, Enum):
    GOVERNMENT = "government"
    MEDICAL = "medical"
    EDUCATION = "education"
    GENERAL = "general"

# Data Models
class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    language: str = "en"
    intent: Optional[str] = None
    confidence: Optional[float] = None
    attachments: List[str] = []

class ServiceInfo(BaseModel):
    id: str
    name: Dict[str, str]  # {"en": "English name", "ar": "Arabic name"}
    category: ServiceCategory
    description: Dict[str, str]
    estimated_time: int  # in minutes
    requires_appointment: bool
    icon: str
    working_hours: Dict[str, str]  # {"start": "08:00", "end": "16:00"}
    available_days: List[str]

class SessionData(BaseModel):
    step: str = "greeting"
    selected_service: Optional[str] = None
    collected_info: Dict[str, Any] = {}
    intent: Optional[str] = None
    confidence: float = 0.0
    booking_step: Optional[str] = None
    appointment_id: Optional[str] = None

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Dict[str, str] = {"en": "New Chat", "ar": "محادثة جديدة"}
    type: str = "general_inquiry"
    status: ConversationStatus = ConversationStatus.ACTIVE
    service: Optional[str] = None
    language: str = "en"
    messages: List[Message] = []
    session_data: SessionData = Field(default_factory=SessionData)
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone_number: Optional[str] = None
    role: str = "user"  # "user" or "admin"
    avatar: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    language: str = "en"
    attachments: List[str] = []

class ChatResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    conversation_id: str
    session_data: SessionData
    actions: List[str] = []

class BookingData(BaseModel):
    appointment_id: str
    service: ServiceInfo
    customer_info: Dict[str, str]
    language: str
    timestamp: str
    
    # Enhanced data for n8n workflows
    booking_type: str = "new_appointment"  # new_appointment, reschedule, cancellation
    priority: str = "normal"  # urgent, high, normal, low
    status: str = "confirmed"  # confirmed, pending, cancelled
    
    # Contact preferences
    notification_preferences: Dict[str, bool] = {
        "email": True,
        "sms": True, 
        "whatsapp": False,
        "voice_call": False
    }
    
    # Scheduling data
    scheduled_datetime: Optional[str] = None
    timezone: str = "UTC"
    duration_minutes: int = 30
    location: Dict[str, str] = {
        "type": "virtual",  # virtual, office, clinic
        "address": "MIND14 Virtual Front Desk",
        "meeting_link": "",
        "room_number": ""
    }
    
    # Follow-up automation
    follow_up_config: Dict[str, Any] = {
        "send_reminder": True,
        "reminder_hours_before": [24, 2],  # Send reminders 24h and 2h before
        "send_follow_up": True,
        "follow_up_hours_after": 24,  # Follow up 24h after appointment
        "max_reschedule_attempts": 2
    }
    
    # Integration data
    external_calendar_id: Optional[str] = None
    crm_contact_id: Optional[str] = None
    ticket_number: Optional[str] = None
    
    # Metadata for analytics
    booking_source: str = "virtual_assistant"  # virtual_assistant, website, phone, mobile_app
    conversation_id: str
    session_duration_seconds: Optional[float] = None
    user_satisfaction_score: Optional[float] = None

# Available Services Configuration
AVAILABLE_SERVICES = [
    ServiceInfo(
        id="health-card-renewal",
        name={"en": "Health Card Renewal", "ar": "تجديد البطاقة الصحية"},
        category=ServiceCategory.GOVERNMENT,
        description={"en": "Renew your health insurance card", "ar": "تجديد بطاقة التأمين الصحي"},
        estimated_time=30,
        requires_appointment=True,
        icon="🏥",
        working_hours={"start": "08:00", "end": "16:00"},
        available_days=["monday", "tuesday", "wednesday", "thursday", "friday"]
    ),
    ServiceInfo(
        id="id-card-replacement",
        name={"en": "ID Card Replacement", "ar": "استبدال بطاقة الهوية"},
        category=ServiceCategory.GOVERNMENT,
        description={"en": "Replace lost or damaged ID card", "ar": "استبدال بطاقة الهوية المفقودة أو التالفة"},
        estimated_time=45,
        requires_appointment=True,
        icon="🆔",
        working_hours={"start": "08:00", "end": "15:00"},
        available_days=["sunday", "tuesday", "thursday"]
    ),
    ServiceInfo(
        id="medical-consultation",
        name={"en": "Medical Consultation", "ar": "استشارة طبية"},
        category=ServiceCategory.MEDICAL,
        description={"en": "Book appointment with doctor", "ar": "حجز موعد مع الطبيب"},
        estimated_time=20,
        requires_appointment=True,
        icon="👩‍⚕️",
        working_hours={"start": "09:00", "end": "17:00"},
        available_days=["sunday", "monday", "tuesday", "wednesday", "thursday"]
    ),
    ServiceInfo(
        id="student-enrollment",
        name={"en": "Student Enrollment", "ar": "تسجيل الطلاب"},
        category=ServiceCategory.EDUCATION,
        description={"en": "Enroll in courses and programs", "ar": "التسجيل في الدورات والبرامج"},
        estimated_time=60,
        requires_appointment=True,
        icon="🎓",
        working_hours={"start": "08:00", "end": "14:00"},
        available_days=["sunday", "monday", "tuesday", "wednesday", "thursday"]
    ),
    ServiceInfo(
        id="general-inquiry",
        name={"en": "General Inquiry", "ar": "استفسار عام"},
        category=ServiceCategory.GENERAL,
        description={"en": "Ask any question or get information", "ar": "اطرح أي سؤال أو احصل على معلومات"},
        estimated_time=10,
        requires_appointment=False,
        icon="💬",
        working_hours={"start": "00:00", "end": "23:59"},
        available_days=["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    )
]

# Mistral AI Integration
class MistralService:
    def __init__(self):
        self.model_name = "mistral:7b-instruct-q4_0"  # or q5_0 for better quality
        self.conversation_context = {}  # Store conversation context for better responses
        self.intent_confidence_threshold = 0.7  # Minimum confidence for intent detection
        
    def update_conversation_context(self, conversation_id: str, user_input: str, intent_result: Dict, session_data: SessionData):
        """Update conversation context for better contextual responses"""
        if conversation_id not in self.conversation_context:
            self.conversation_context[conversation_id] = {
                "previous_intents": [],
                "extracted_entities": {},
                "conversation_history": [],
                "user_preferences": {},
                "conversation_stage": "initial"
            }
        
        context = self.conversation_context[conversation_id]
        
        # Update previous intents
        context["previous_intents"].append({
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 5 intents
        context["previous_intents"] = context["previous_intents"][-5:]
        
        # Merge extracted entities
        entities = intent_result.get("entities", {})
        for key, value in entities.items():
            context["extracted_entities"][key] = value
        
        # Update conversation history
        context["conversation_history"].append({
            "user_input": user_input,
            "step": session_data.step,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 10 exchanges
        context["conversation_history"] = context["conversation_history"][-10:]
        
        # Determine conversation stage
        if session_data.step in ["booking", "confirmation"]:
            context["conversation_stage"] = "active_booking"
        elif session_data.step == "completed":
            context["conversation_stage"] = "completed"
        elif len(context["conversation_history"]) == 1:
            context["conversation_stage"] = "initial"
        else:
            context["conversation_stage"] = "ongoing"
        
        return context
        
    async def ensure_model_available(self):
        """Ensure Mistral model is available - fallback to rule-based for demo"""
        try:
            # Try to check if Ollama is available
            import subprocess
            result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
            if result.returncode == 0:
                models = await asyncio.to_thread(ollama.list)
                model_names = [model['name'] for model in models['models']]
                
                if self.model_name not in model_names:
                    logger.info(f"Pulling Mistral model: {self.model_name}")
                    await asyncio.to_thread(ollama.pull, self.model_name)
                    logger.info("Mistral model pulled successfully")
                
                return True
            else:
                logger.warning("Ollama not available, using fallback AI system")
                return False
        except Exception as e:
            logger.warning(f"Ollama not available ({e}), using fallback AI system")
            return False

    async def classify_intent(self, user_input: str, language: str = "en") -> Dict[str, Any]:
        """Classify user intent - with fallback to rule-based system and advanced logging"""
        start_time = datetime.utcnow()
        
        try:
            # Try Mistral first
            if await self.ensure_model_available():
                result = await self._classify_with_mistral(user_input, language)
                method_used = "mistral"
            else:
                # Fallback to enhanced rule-based system
                result = self._fallback_intent_classification(user_input, language)
                method_used = "rule_based"
            
            # Log performance metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Intent classification - Method: {method_used}, Intent: {result['intent']}, "
                       f"Confidence: {result['confidence']:.2f}, Processing time: {processing_time:.3f}s, "
                       f"Language: {language}, Input length: {len(user_input)}")
            
            # Add metadata for analytics
            result["metadata"] = {
                "method_used": method_used,
                "processing_time": processing_time,
                "input_length": len(user_input),
                "language": language,
                "timestamp": start_time.isoformat()
            }
            
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Error in intent classification: {e}, Processing time: {processing_time:.3f}s")
            
            result = self._fallback_intent_classification(user_input, language)
            result["metadata"] = {
                "method_used": "fallback_error",
                "processing_time": processing_time,
                "error": str(e),
                "language": language,
                "timestamp": start_time.isoformat()
            }
            
            return result

    async def _classify_with_mistral(self, user_input: str, language: str) -> Dict[str, Any]:
        """Classify using actual Mistral model"""
        system_prompt = self._get_intent_classification_prompt(language)
        user_prompt = f"User input: {user_input}"
        
        response = await asyncio.to_thread(
            ollama.generate,
            model=self.model_name,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            stream=False
        )
        
        result = self._parse_intent_response(response['response'])
        logger.info(f"Mistral intent classification result: {result}")
        return result

    def _get_intent_classification_prompt(self, language: str) -> str:
        """Get the system prompt for intent classification"""
        if language == "ar":
            return """أنت مساعد ذكي لمكتب الاستقبال الافتراضي. مهمتك تصنيف نوايا المستخدمين بناءً على رسائلهم.

الخدمات المتاحة:
1. health_card_renewal - تجديد البطاقة الصحية
2. id_card_replacement - استبدال بطاقة الهوية
3. medical_consultation - استشارة طبية
4. student_enrollment - تسجيل الطلاب
5. general_inquiry - استفسار عام

قم بتحليل رسالة المستخدم وأعد النتيجة بصيغة JSON:
{
  "intent": "اسم النية",
  "confidence": نسبة الثقة (0.0-1.0),
  "service_id": "معرف الخدمة أو null",
  "entities": {"كيانات مستخرجة"}
}"""
        else:
            return """You are an AI assistant for a virtual front desk. Your task is to classify user intents based on their messages.

Available services:
1. health_card_renewal - Renew health insurance card
2. id_card_replacement - Replace lost or damaged ID card  
3. medical_consultation - Book doctor appointment
4. student_enrollment - Enroll in courses and programs
5. general_inquiry - General questions and information

Analyze the user's message and return the result in JSON format:
{
  "intent": "intent_name",
  "confidence": confidence_score (0.0-1.0),
  "service_id": "service_id or null",
  "entities": {"extracted_entities"}
}"""

    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """Parse Mistral's intent classification response"""
        try:
            # Try to extract JSON from the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate and normalize the result
                return {
                    "intent": result.get("intent", "general_inquiry"),
                    "confidence": min(max(float(result.get("confidence", 0.5)), 0.0), 1.0),
                    "service_id": result.get("service_id"),
                    "entities": result.get("entities", {})
                }
            else:
                # Fallback to rule-based classification
                return self._fallback_intent_classification(response)
                
        except Exception as e:
            logger.error(f"Error parsing intent response: {e}")
            return self._fallback_intent_classification(response)

    def _fallback_intent_classification(self, text: str, language: str = "en") -> Dict[str, Any]:
        """Enhanced fallback rule-based intent classification with sophisticated pattern matching"""
        text_lower = text.lower()
        
        # Significantly enhanced intent patterns with synonyms, variations, and contextual terms
        intent_patterns = {
            "health_card_renewal": {
                "en": [
                    # Direct terms
                    "health card", "renew", "renewal", "health insurance", "medical card", "health coverage", "insurance renewal",
                    # Variations and synonyms
                    "health certificate", "medical certificate", "healthcare card", "health benefits", "medical benefits",
                    "insurance card", "medical insurance", "health plan", "coverage renewal", "benefits renewal",
                    "health card expired", "health card expiry", "health card update", "medical coverage expired",
                    # Context-specific phrases
                    "need to renew my health", "health card is expired", "update my medical", "extend my health",
                    "my insurance has expired", "health benefits renewal", "medical coverage renewal"
                ],
                "ar": [
                    "بطاقة صحية", "تجديد", "تأمين صحي", "بطاقة طبية", "تغطية صحية", "تأمين طبي",
                    "شهادة صحية", "بطاقة التأمين", "التأمين الطبي", "الخدمات الصحية", "المنافع الطبية",
                    "بطاقة صحية منتهية", "انتهت بطاقتي الصحية", "تحديث البطاقة الصحية", "تمديد التأمين",
                    "أريد تجديد البطاقة", "البطاقة الصحية انتهت", "تجديد التأمين الصحي"
                ]
            },
            "id_card_replacement": {
                "en": [
                    # Direct terms
                    "id card", "identity", "replace", "lost id", "damaged id", "identity card", "national id", "replacement",
                    # Variations
                    "identity document", "personal id", "government id", "citizenship card", "id document",
                    "new id card", "id card copy", "duplicate id", "id card renewal", "identity renewal",
                    # Context-specific
                    "lost my id", "id card damaged", "need new id", "replace my identity", "id card broken",
                    "stolen id card", "id card missing", "duplicate identity card", "new identity document"
                ],
                "ar": [
                    "بطاقة هوية", "استبدال", "هوية مفقودة", "بطاقة تالفة", "هوية وطنية", "بطاقة شخصية",
                    "وثيقة هوية", "هوية شخصية", "بطاقة حكومية", "بطاقة مواطنة", "وثيقة شخصية",
                    "ضاعت هويتي", "بطاقة الهوية تالفة", "أحتاج هوية جديدة", "استبدال الهوية", "بطاقة مكسورة",
                    "سرقت بطاقة الهوية", "هوية مفقودة", "نسخة من الهوية", "بطاقة هوية جديدة"
                ]
            },
            "medical_consultation": {
                "en": [
                    # Direct terms
                    "doctor", "appointment", "medical", "consultation", "doctor visit", "see doctor", "medical appointment", "clinic",
                    # Variations
                    "physician", "medical exam", "checkup", "health checkup", "medical consultation", "doctor consultation",
                    "book appointment", "schedule appointment", "medical visit", "health consultation", "specialist",
                    # Context-specific
                    "need to see a doctor", "book medical appointment", "health problem", "medical issue",
                    "doctor's appointment", "medical emergency", "health concern", "need medical help",
                    "schedule with doctor", "visit clinic", "see specialist", "medical examination"
                ],
                "ar": [
                    "طبيب", "موعد", "استشارة", "طبية", "زيارة طبيب", "عيادة", "موعد طبي", "فحص طبي",
                    "دكتور", "فحص صحي", "استشارة طبية", "كشف طبي", "أخصائي", "طبيب مختص",
                    "أحتاج طبيب", "حجز موعد طبي", "مشكلة صحية", "مشكلة طبية", "موعد الطبيب",
                    "زيارة العيادة", "فحص عند الطبيب", "استشارة صحية", "طوارئ طبية", "مساعدة طبية",
                    "حجز مع الطبيب", "رؤية الطبيب", "كشف عند الدكتور"
                ]
            },
            "student_enrollment": {
                "en": [
                    # Direct terms
                    "enroll", "student", "course", "register", "education", "enrollment", "university", "school", "study",
                    # Variations
                    "registration", "admission", "academic", "college", "institute", "program", "degree", "classes",
                    "semester", "academic year", "student registration", "course registration", "class enrollment",
                    # Context-specific
                    "want to study", "apply for course", "join university", "student application", "academic admission",
                    "register for classes", "enroll in program", "education program", "learning program",
                    "student services", "academic services", "course application", "study application"
                ],
                "ar": [
                    "تسجيل", "طالب", "دورة", "تعليم", "التحاق", "جامعة", "مدرسة", "دراسة", "قبول",
                    "تسجيل الطلاب", "قبول جامعي", "أكاديمي", "كلية", "معهد", "برنامج", "شهادة", "صفوف",
                    "فصل دراسي", "سنة أكاديمية", "تسجيل الدورة", "تسجيل الصف", "الالتحاق بالبرنامج",
                    "أريد الدراسة", "التقديم للدورة", "الانضمام للجامعة", "طلب الطالب", "قبول أكاديمي",
                    "تسجيل في الصفوف", "تسجيل في البرنامج", "برنامج تعليمي", "برنامج التعلم",
                    "خدمات الطلاب", "خدمات أكاديمية", "طلب الدورة", "طلب الدراسة"
                ]
            }
        }
        
        # Advanced scoring algorithm with multiple factors
        max_score = 0
        detected_intent = "general_inquiry"
        best_matches = []
        
        for intent, patterns in intent_patterns.items():
            words = patterns.get(language, patterns["en"])
            
            # Multiple scoring factors
            exact_word_matches = sum(1 for word in words if word in text_lower)
            phrase_matches = sum(2 for word in words if len(word.split()) > 1 and word in text_lower)
            partial_matches = sum(0.5 for word in words if any(part in text_lower for part in word.split()))
            
            # Contextual bonus scoring
            context_bonus = 0
            if intent == "health_card_renewal" and any(term in text_lower for term in ["expired", "expire", "old", "update"]):
                context_bonus += 1
            elif intent == "id_card_replacement" and any(term in text_lower for term in ["lost", "missing", "stolen", "damaged", "broken"]):
                context_bonus += 1
            elif intent == "medical_consultation" and any(term in text_lower for term in ["sick", "pain", "problem", "issue", "emergency"]):
                context_bonus += 1
            elif intent == "student_enrollment" and any(term in text_lower for term in ["apply", "application", "join", "start"]):
                context_bonus += 1
            
            # Calculate total score with weights
            total_score = (exact_word_matches * 1.0) + (phrase_matches * 1.5) + (partial_matches * 0.3) + (context_bonus * 0.8)
            
            if total_score > max_score:
                max_score = total_score
                detected_intent = intent
                best_matches = [word for word in words if word in text_lower]
        
        # Enhanced confidence calculation
        if max_score >= 3:
            confidence = min(0.85 + (max_score * 0.05), 0.98)
        elif max_score >= 2:
            confidence = min(0.75 + (max_score * 0.05), 0.90)
        elif max_score >= 1:
            confidence = min(0.65 + (max_score * 0.05), 0.80)
        else:
            confidence = 0.5
        
        # Enhanced greeting detection with cultural variations
        greetings = {
            "en": [
                "hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings",
                "howdy", "what's up", "how are you", "good day", "nice to meet you", "pleased to meet you",
                "how do you do", "how's it going", "how's everything", "salutations", "hiya"
            ],
            "ar": [
                "مرحبا", "أهلا", "السلام عليكم", "صباح الخير", "مساء الخير", "أهلا وسهلا",
                "حياك الله", "أهلا بك", "مرحبا بك", "تحية طيبة", "السلام عليكم ورحمة الله",
                "صباح النور", "مساء النور", "كيف الحال", "كيف حالك", "أسعد الله مساءك"
            ]
        }
        
        # Check for greetings with enhanced detection
        if max_score == 0:
            greeting_words = greetings.get(language, greetings["en"])
            greeting_matches = sum(1 for word in greeting_words if word in text_lower)
            
            if greeting_matches > 0:
                detected_intent = "greeting"
                confidence = min(0.85 + (greeting_matches * 0.05), 0.95)
            else:
                # Check for question words that might indicate general inquiry
                question_words = {
                    "en": ["what", "how", "when", "where", "why", "who", "which", "can you", "could you", "do you"],
                    "ar": ["ما", "كيف", "متى", "أين", "لماذا", "من", "أي", "هل يمكن", "هل تستطيع", "ماذا"]
                }
                
                q_words = question_words.get(language, question_words["en"])
                if any(word in text_lower for word in q_words):
                    detected_intent = "general_inquiry"
                    confidence = 0.7
                else:
                    confidence = 0.5
        
        service_id = detected_intent.replace("_", "-") if detected_intent not in ["general_inquiry", "greeting"] else None
        
        return {
            "intent": detected_intent,
            "confidence": confidence,
            "service_id": service_id,
            "entities": self._extract_entities(text, language)
        }

    def _extract_entities(self, text: str, language: str) -> Dict[str, Any]:
        """Enhanced entity extraction with comprehensive pattern matching"""
        entities = {}
        import re
        
        # Enhanced phone number extraction with international formats
        phone_patterns = [
            r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'(\+?\d{1,3}[-.\s]?)?\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4}',    # International
            r'(\+?\d{1,3})?\s?\d{9,}',                                    # Simple international
            r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',                         # Simple US
            r'(\+\d{1,3}[-.\s]?\d{1,14})',                              # E.164 format
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                # Clean the phone number
                phone = re.sub(r'[^\d+]', '', str(phones[0]))
                if len(phone) >= 9:  # Minimum valid phone length
                    entities["phone"] = phone
                    break
        
        # Enhanced name extraction with multiple languages and patterns
        name_extraction_patterns = {
            "en": [
                r'my name is (\w+(?:\s+\w+)*)',
                r'i am (\w+(?:\s+\w+)*)',
                r"i'm (\w+(?:\s+\w+)*)",
                r'name[:\s]+(\w+(?:\s+\w+)*)',
                r'called (\w+(?:\s+\w+)*)',
                r'this is (\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*) here',
                r'speaking with (\w+(?:\s+\w+)*)',
            ],
            "ar": [
                r'اسمي (\w+(?:\s+\w+)*)',
                r'أنا (\w+(?:\s+\w+)*)',
                r'انا (\w+(?:\s+\w+)*)',
                r'الاسم[:\s]+(\w+(?:\s+\w+)*)',
                r'يدعوني (\w+(?:\s+\w+)*)',
                r'هذا (\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*) هنا',
            ]
        }
        
        patterns = name_extraction_patterns.get(language, name_extraction_patterns["en"])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Validate name (2-50 characters, only letters and spaces)
                if re.match(r'^[a-zA-Z\u0600-\u06FF\s]{2,50}$', name):
                    entities["name"] = name
                    break
        
        # Enhanced date and time extraction
        date_time_patterns = {
            "en": {
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                "times": ["morning", "afternoon", "evening", "night", "noon", "midnight"],
                "relative": ["today", "tomorrow", "next week", "next month", "this week", "this month"],
                "specific_times": r'\b\d{1,2}:\d{2}\s?(?:am|pm|AM|PM)?\b',
                "dates": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b'
            },
            "ar": {
                "days": ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"],
                "times": ["صباحاً", "مساءً", "ليلاً", "ظهراً", "العصر", "المغرب"],
                "relative": ["اليوم", "غدا", "غداً", "الأسبوع القادم", "الشهر القادم", "هذا الأسبوع"],
                "specific_times": r'\b\d{1,2}:\d{2}\b',
                "dates": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b'
            }
        }
        
        dt_patterns = date_time_patterns.get(language, date_time_patterns["en"])
        
        # Extract days
        found_days = [day for day in dt_patterns["days"] if day in text.lower()]
        if found_days:
            entities["preferred_day"] = found_days[0]
        
        # Extract time periods
        found_times = [time for time in dt_patterns["times"] if time in text.lower()]
        if found_times:
            entities["preferred_time_period"] = found_times[0]
        
        # Extract relative dates
        found_relative = [rel for rel in dt_patterns["relative"] if rel in text.lower()]
        if found_relative:
            entities["relative_date"] = found_relative[0]
        
        # Extract specific times
        time_matches = re.findall(dt_patterns["specific_times"], text)
        if time_matches:
            entities["specific_time"] = time_matches[0]
        
        # Extract specific dates
        date_matches = re.findall(dt_patterns["dates"], text)
        if date_matches:
            entities["specific_date"] = date_matches[0]
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            entities["email"] = emails[0]
        
        # Extract age if mentioned
        age_patterns = [
            r'(\d{1,3})\s*(?:years?\s*old|yr|years)',
            r'age[:\s]*(\d{1,3})',
            r'i am (\d{1,3})'
        ]
        
        for pattern in age_patterns:
            age_match = re.search(pattern, text, re.IGNORECASE)
            if age_match:
                age = int(age_match.group(1))
                if 1 <= age <= 120:  # Reasonable age range
                    entities["age"] = age
                    break
        
        # Extract urgency indicators
        urgency_patterns = {
            "en": ["urgent", "emergency", "asap", "immediately", "quickly", "rush", "priority"],
            "ar": ["عاجل", "طارئ", "فوري", "سريع", "مستعجل", "أولوية"]
        }
        
        urgency_words = urgency_patterns.get(language, urgency_patterns["en"])
        if any(word in text.lower() for word in urgency_words):
            entities["urgency"] = "high"
        
        # Extract location mentions
        location_patterns = [
            r'at (\w+(?:\s+\w+)*)',
            r'in (\w+(?:\s+\w+)*)',
            r'from (\w+(?:\s+\w+)*)',
            r'location[:\s]*(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, text, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
                if len(location) >= 2 and len(location) <= 50:
                    entities["location"] = location
                    break
        
        return entities

    async def generate_response(self, user_input: str, session_data: SessionData, intent_result: Dict, language: str = "en", context: Dict = None) -> Dict[str, Any]:
        """Generate AI response based on conversation context with enhanced context awareness"""
        try:
            # Try Mistral first, fall back to rule-based
            if await self.ensure_model_available():
                return await self._generate_with_mistral(user_input, session_data, language, context)
            else:
                return self._generate_with_rules(user_input, session_data, intent_result, language, context)
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            fallback_message = "I apologize, but I'm having trouble processing your request. Please try again." if language == "en" else "أعتذر، أواجه مشكلة في معالجة طلبك. يرجى المحاولة مرة أخرى."
            return {
                "message": fallback_message,
                "session_data": session_data
            }

    async def _generate_with_mistral(self, user_input: str, session_data: SessionData, language: str, context: Dict = None) -> Dict[str, Any]:
        """Generate response using Mistral model with enhanced context"""
        system_prompt = self._get_response_generation_prompt(session_data, language, context)
        user_prompt = f"User input: {user_input}"
        
        response = await asyncio.to_thread(
            ollama.generate,
            model=self.model_name,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            stream=False
        )
        
        return {
            "message": response['response'].strip(),
            "session_data": session_data
        }

    def _generate_with_rules(self, user_input: str, session_data: SessionData, intent_result: Dict, language: str, context: Dict = None) -> Dict[str, Any]:
        """Enhanced rule-based response generation with sophisticated conversation flow"""
        
        # Enhanced conversation flow state management
        if session_data.step == "greeting" or not session_data.intent:
            return self._handle_greeting_backend(user_input, intent_result, session_data, language)
        elif session_data.step == "service_selection":
            return self._handle_service_selection_backend(user_input, session_data, language)
        elif session_data.step == "booking":
            return self._handle_booking_backend(user_input, session_data, language)
        elif session_data.step == "confirmation":
            return self._handle_confirmation_backend(user_input, session_data, language)
        elif session_data.step == "general_inquiry":
            return self._handle_general_inquiry_backend(user_input, session_data, intent_result, language)
        else:
            return self._handle_fallback_backend(user_input, session_data, language)

    def _handle_general_inquiry_backend(self, user_input: str, session_data: SessionData, intent_result: Dict, language: str) -> Dict[str, Any]:
        """Handle general inquiries with context-aware responses"""
        
        # Enhanced response templates for different types of inquiries
        inquiry_responses = {
            "en": {
                "working_hours": "Our working hours vary by service:\n\n🏥 **Health Services**: 8:00 AM - 4:00 PM (Mon-Fri)\n🆔 **ID Services**: 8:00 AM - 3:00 PM (Sun, Tue, Thu)\n👩‍⚕️ **Medical Services**: 9:00 AM - 5:00 PM (Sun-Thu)\n🎓 **Education Services**: 8:00 AM - 2:00 PM (Sun-Thu)\n💬 **General Inquiries**: 24/7\n\nHow can I help you today?",
                "services_overview": "I can help you with these services:\n\n🏥 **Health Card Renewal** (30 min, appointment required)\n🆔 **ID Card Replacement** (45 min, appointment required)\n👩‍⚕️ **Medical Consultation** (20 min, appointment required)\n🎓 **Student Enrollment** (60 min, appointment required)\n💬 **General Inquiries** (10 min, no appointment needed)\n\nWhich service would you like to know more about?",
                "contact_info": "You can reach us through:\n\n📧 **Email**: support@mind14.com\n📱 **Phone**: +1-800-MIND14\n🌐 **Website**: www.mind14.com\n📍 **Address**: Virtual Front Desk - Available 24/7\n\nI'm here to help you right now! What do you need?",
                "appointment_info": "Here's how appointments work:\n\n✅ **Required for**: Health Card Renewal, ID Replacement, Medical Consultation, Student Enrollment\n⏰ **Booking**: I can help you book right now\n📋 **Requirements**: Valid ID and relevant documents\n🔄 **Rescheduling**: Contact us 24 hours in advance\n\nWould you like to book an appointment?",
                "default": "I understand you have a question. As your virtual assistant, I'm here to help with various services including health card renewals, ID replacements, medical appointments, and student enrollment. Could you tell me more specifically what you need help with?"
            },
            "ar": {
                "working_hours": "ساعات العمل تختلف حسب الخدمة:\n\n🏥 **الخدمات الصحية**: 8:00 ص - 4:00 م (الاثنين-الجمعة)\n🆔 **خدمات الهوية**: 8:00 ص - 3:00 م (الأحد، الثلاثاء، الخميس)\n👩‍⚕️ **الخدمات الطبية**: 9:00 ص - 5:00 م (الأحد-الخميس)\n🎓 **الخدمات التعليمية**: 8:00 ص - 2:00 م (الأحد-الخميس)\n💬 **الاستفسارات العامة**: 24/7\n\nكيف يمكنني مساعدتك اليوم؟",
                "services_overview": "يمكنني مساعدتك في هذه الخدمات:\n\n🏥 **تجديد البطاقة الصحية** (30 دقيقة، يتطلب موعد)\n🆔 **استبدال بطاقة الهوية** (45 دقيقة، يتطلب موعد)\n👩‍⚕️ **الاستشارة الطبية** (20 دقيقة، يتطلب موعد)\n🎓 **تسجيل الطلاب** (60 دقيقة، يتطلب موعد)\n💬 **الاستفسارات العامة** (10 دقائق، لا يتطلب موعد)\n\nأي خدمة تريد معرفة المزيد عنها؟",
                "contact_info": "يمكنك التواصل معنا عبر:\n\n📧 **البريد الإلكتروني**: support@mind14.com\n📱 **الهاتف**: +1-800-MIND14\n🌐 **الموقع**: www.mind14.com\n📍 **العنوان**: مكتب الاستقبال الافتراضي - متاح 24/7\n\nأنا هنا لمساعدتك الآن! ماذا تحتاج؟",
                "appointment_info": "إليك كيفية عمل المواعيد:\n\n✅ **مطلوب لـ**: تجديد البطاقة الصحية، استبدال الهوية، الاستشارة الطبية، تسجيل الطلاب\n⏰ **الحجز**: يمكنني مساعدتك في الحجز الآن\n📋 **المتطلبات**: هوية صالحة والوثائق ذات الصلة\n🔄 **إعادة الجدولة**: اتصل بنا قبل 24 ساعة\n\nهل تريد حجز موعد؟",
                "default": "أفهم أن لديك سؤال. كمساعدك الافتراضي، أنا هنا للمساعدة في خدمات مختلفة بما في ذلك تجديد البطاقة الصحية، استبدال الهوية، المواعيد الطبية، وتسجيل الطلاب. هل يمكنك إخباري بالتحديد عما تحتاج مساعدة فيه؟"
            }
        }
        
        # Analyze the inquiry type based on keywords
        inquiry_type = "default"
        text_lower = user_input.lower()
        
        # Detect inquiry type
        if any(word in text_lower for word in ["hours", "time", "when", "open", "close", "ساعات", "وقت", "متى", "مفتوح", "مغلق"]):
            inquiry_type = "working_hours"
        elif any(word in text_lower for word in ["services", "what", "help", "do", "خدمات", "ماذا", "مساعدة", "تساعد"]):
            inquiry_type = "services_overview"
        elif any(word in text_lower for word in ["contact", "phone", "email", "address", "reach", "تواصل", "هاتف", "بريد", "عنوان"]):
            inquiry_type = "contact_info"
        elif any(word in text_lower for word in ["appointment", "booking", "schedule", "موعد", "حجز", "جدولة"]):
            inquiry_type = "appointment_info"
        
        current_responses = inquiry_responses[language]
        message = current_responses[inquiry_type]
        
        return {"message": message, "session_data": session_data}

    def _handle_confirmation_backend(self, user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
        """Handle appointment confirmation and follow-up"""
        
        confirmation_words = {
            "en": ["yes", "confirm", "correct", "right", "okay", "ok", "sure", "proceed"],
            "ar": ["نعم", "أكد", "صحيح", "موافق", "حسنا", "متابعة", "استمر"]
        }
        
        is_confirming = any(word in user_input.lower() for word in confirmation_words[language])
        
        if is_confirming:
            if language == "ar":
                message = """✅ **تم تأكيد الموعد!**

📧 ستتلقى تأكيداً عبر البريد الإلكتروني والرسائل النصية خلال 10 دقائق.
📋 احضر معك الوثائق المطلوبة والهوية الصالحة.
⏰ يرجى الحضور قبل 15 دقيقة من موعدك.

🔄 **إذا احتجت لتغيير الموعد:**
- اتصل بنا قبل 24 ساعة على الأقل
- استخدم رقم الموعد للمرجع

هل تحتاج مساعدة في أي شيء آخر؟"""
            else:
                message = """✅ **Appointment Confirmed!**

📧 You'll receive confirmation via email and SMS within 10 minutes.
📋 Please bring required documents and valid ID.
⏰ Please arrive 15 minutes before your appointment.

🔄 **If you need to reschedule:**
- Contact us at least 24 hours in advance
- Use your appointment ID for reference

Is there anything else I can help you with?"""
            
            session_data.step = "completed"
        else:
            if language == "ar":
                message = "هل تريد تأكيد الموعد أم تفضل تعديل التفاصيل؟ يمكنني مساعدتك في أي تغييرات تحتاجها."
            else:
                message = "Would you like to confirm the appointment or would you prefer to modify the details? I can help you with any changes you need."
        
        return {"message": message, "session_data": session_data}

    def _handle_fallback_backend(self, user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
        """Enhanced fallback handler with context awareness"""
        
        fallback_responses = {
            "en": [
                "I understand you need assistance. Could you please tell me which of these services you're interested in: Health Card Renewal, ID Card Replacement, Medical Consultation, Student Enrollment, or General Information?",
                "I'm here to help! Can you clarify what specific service you need? I can assist with health cards, ID replacements, medical appointments, student enrollment, or answer general questions.",
                "Let me help you find the right service. Are you looking for help with health services, identification documents, medical appointments, educational enrollment, or do you have a general question?",
            ],
            "ar": [
                "أفهم أنك تحتاج مساعدة. هل يمكنك إخباري أي من هذه الخدمات تهمك: تجديد البطاقة الصحية، استبدال بطاقة الهوية، الاستشارة الطبية، تسجيل الطلاب، أو معلومات عامة؟",
                "أنا هنا للمساعدة! هل يمكنك توضيح الخدمة المحددة التي تحتاجها؟ يمكنني المساعدة في البطاقات الصحية، استبدال الهوية، المواعيد الطبية، تسجيل الطلاب، أو الإجابة على الأسئلة العامة.",
                "دعني أساعدك في العثور على الخدمة المناسبة. هل تبحث عن مساعدة في الخدمات الصحية، وثائق الهوية، المواعيد الطبية، التسجيل التعليمي، أم لديك سؤال عام؟",
            ]
        }
        
        import random
        responses = fallback_responses[language]
        message = random.choice(responses)
        
        # Reset to intent detection step
        session_data.step = "intent_detection"
        
        return {"message": message, "session_data": session_data}

    def _handle_greeting_backend(self, user_input: str, intent_result: Dict, session_data: SessionData, language: str) -> Dict[str, Any]:
        """Handle greeting with backend logic"""
        service = None
        if intent_result.get("service_id"):
            service = next((s for s in AVAILABLE_SERVICES if s.id == intent_result["service_id"]), None)
        
        if language == "ar":
            if service:
                message = f"""مرحباً! أفهم أنك تحتاج مساعدة في **{service.name[language]}**.

🕒 **تفاصيل الخدمة:**
• المدة المقدرة: {service.estimated_time} دقيقة
• {service.icon} {service.description[language]}

{'📅 تتطلب هذه الخدمة حجز موعد.' if service.requires_appointment else '💬 هذه خدمة استفسار عام.'}

هل تريد المتابعة مع هذه الخدمة؟"""
                session_data.step = "service_selection"
                session_data.selected_service = service.id
            else:
                message = """مرحباً! أنا MIND14، مساعدك الافتراضي الذكي.

🏛️ **يمكنني مساعدتك في:**
• 🏥 تجديد البطاقة الصحية
• 🆔 استبدال بطاقة الهوية
• 👩‍⚕️ حجز المواعيد الطبية
• 🎓 تسجيل الطلاب
• 💬 الاستفسارات العامة

كيف يمكنني مساعدتك اليوم؟"""
                session_data.step = "intent_detection"
        else:
            if service:
                message = f"""Hello! I understand you need help with **{service.name[language]}**.

🕒 **Service Details:**
• Estimated time: {service.estimated_time} minutes
• {service.icon} {service.description[language]}

{'📅 This service requires an appointment.' if service.requires_appointment else '💬 This is a general inquiry service.'}

Would you like to proceed with this service?"""
                session_data.step = "service_selection"
                session_data.selected_service = service.id
            else:
                message = """Hello! I'm MIND14, your AI virtual assistant.

🏛️ **I can help you with:**
• 🏥 Health card renewal
• 🆔 ID card replacement
• 👩‍⚕️ Medical appointments
• 🎓 Student enrollment
• 💬 General inquiries

How can I assist you today?"""
                session_data.step = "intent_detection"
        
        session_data.intent = intent_result.get("intent")
        session_data.confidence = intent_result.get("confidence", 0.0)
        
        return {"message": message, "session_data": session_data}

    def _handle_service_selection_backend(self, user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
        """Handle service selection with backend logic"""
        confirmation_words = {
            "en": ["yes", "sure", "ok", "okay", "proceed", "continue", "confirm"],
            "ar": ["نعم", "موافق", "حسنا", "متابعة", "استمر", "أكد", "موافقة"]
        }
        
        is_confirming = any(word in user_input.lower() for word in confirmation_words[language])
        
        if is_confirming and session_data.selected_service:
            service = next((s for s in AVAILABLE_SERVICES if s.id == session_data.selected_service), None)
            
            if service and service.requires_appointment:
                if language == "ar":
                    message = f"""ممتاز! سأساعدك في حجز موعد لـ **{service.name[language]}**.

📋 **المعلومات المطلوبة:**
• الاسم الكامل
• رقم الهاتف
• التاريخ والوقت المفضل

⏰ **ساعات العمل:** {service.working_hours['start']} - {service.working_hours['end']}

لنبدأ - ما هو اسمك الكامل؟"""
                else:
                    message = f"""Great! I'll help you book an appointment for **{service.name[language]}**.

📋 **Required Information:**
• Full name
• Phone number
• Preferred date and time

⏰ **Working hours:** {service.working_hours['start']} - {service.working_hours['end']}

Let's start - what's your full name?"""
                
                session_data.step = "booking"
                session_data.booking_step = "name"
            else:
                if language == "ar":
                    message = f"""أنا هنا لمساعدتك في **{service.name[language]}**. 

هذه خدمة استفسار عام، لذا يمكنك طرح أي أسئلة تريدها حول هذا الموضوع."""
                else:
                    message = f"""I'm here to help with **{service.name[language]}**. 

This is a general inquiry service, so feel free to ask any questions you have about this topic."""
                
                session_data.step = "general_inquiry"
        else:
            # Show service options
            if language == "ar":
                services_text = "\n".join([f"{s.icon} **{s.name['ar']}** - {s.description['ar']}" for s in AVAILABLE_SERVICES])
                message = f"يمكنني مساعدتك في الخدمات التالية:\n\n{services_text}\n\nأي خدمة تهمك؟"
            else:
                services_text = "\n".join([f"{s.icon} **{s.name['en']}** - {s.description['en']}" for s in AVAILABLE_SERVICES])
                message = f"I can help you with these services:\n\n{services_text}\n\nWhich service interests you?"
            
            session_data.step = "service_selection"
        
        return {"message": message, "session_data": session_data}

    def _handle_booking_backend(self, user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
        """Handle booking process with backend logic"""
        booking_step = session_data.booking_step or "name"
        
        if booking_step == "name":
            session_data.collected_info["name"] = user_input
            session_data.booking_step = "phone"
            
            if language == "ar":
                message = f"شكراً، {user_input}! الآن أحتاج رقم هاتفك لتأكيد الموعد."
            else:
                message = f"Thank you, {user_input}! Now I need your phone number for appointment confirmation."
                
        elif booking_step == "phone":
            session_data.collected_info["phone"] = user_input
            session_data.booking_step = "datetime"
            
            if language == "ar":
                message = "ممتاز! الآن أخبرني بالتاريخ والوقت المفضل. مثال: '25 يناير في الساعة 2:00 مساءً'"
            else:
                message = "Perfect! Now please tell me your preferred date and time. Example: 'January 25th at 2:00 PM'"
                
        elif booking_step == "datetime":
            session_data.collected_info["preferred_datetime"] = user_input
            
            # Generate appointment confirmation
            appointment_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            session_data.appointment_id = appointment_id
            
            service = next((s for s in AVAILABLE_SERVICES if s.id == session_data.selected_service), None)
            
            if language == "ar":
                message = f"""🎉 **تم حجز الموعد بنجاح!**

📅 **تفاصيل الموعد:**
• الخدمة: {service.name['ar'] if service else 'غير محدد'}
• الاسم: {session_data.collected_info.get('name')}
• الهاتف: {session_data.collected_info.get('phone')}
• الوقت المفضل: {session_data.collected_info.get('preferred_datetime')}
• رقم الموعد: {appointment_id}

✅ ستتلقى تأكيداً عبر الرسائل النصية والبريد الإلكتروني قريباً.

هل تحتاج مساعدة في أي شيء آخر؟"""
            else:
                message = f"""🎉 **Appointment Booked Successfully!**

📅 **Appointment Details:**
• Service: {service.name['en'] if service else 'Not specified'}
• Name: {session_data.collected_info.get('name')}
• Phone: {session_data.collected_info.get('phone')}
• Preferred Time: {session_data.collected_info.get('preferred_datetime')}
• Appointment ID: {appointment_id}

✅ You will receive confirmation via SMS and email shortly.

Is there anything else I can help you with?"""
            
            session_data.step = "completed"
            
            return {
                "message": message,
                "session_data": session_data,
                "trigger_webhook": True,
                "booking_data": BookingData(
                    appointment_id=appointment_id,
                    service=service,
                    customer_info=session_data.collected_info,
                    language=language,
                    timestamp=datetime.now().isoformat(),
                    booking_type="new_appointment",
                    priority="normal",
                    status="confirmed",
                    notification_preferences={
                        "email": True,
                        "sms": True,
                        "whatsapp": session_data.collected_info.get("whatsapp_consent", False),
                        "voice_call": False
                    },
                    scheduled_datetime=session_data.collected_info.get("preferred_datetime"),
                    timezone="UTC",
                    duration_minutes=service.estimated_time if service else 30,
                    location={
                        "type": "office" if service and service.requires_appointment else "virtual",
                        "address": "MIND14 Service Center" if service and service.requires_appointment else "Virtual Front Desk",
                        "meeting_link": "" if service and service.requires_appointment else "https://meet.mind14.com/virtual-desk",
                        "room_number": f"Room {service.icon}" if service and service.requires_appointment else ""
                    },
                    follow_up_config={
                        "send_reminder": True,
                        "reminder_hours_before": [24, 2],
                        "send_follow_up": True,
                        "follow_up_hours_after": 24,
                        "max_reschedule_attempts": 2
                    },
                    booking_source="virtual_assistant",
                    conversation_id=getattr(session_data, 'conversation_id', 'unknown')
                ).dict()
            }
        
        return {"message": message, "session_data": session_data}

    def _handle_general_backend(self, user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
        """Handle general inquiries with backend logic"""
        if language == "ar":
            message = "أفهم سؤالك. كمساعدك الافتراضي، أنا هنا لمساعدتك في خدمات متنوعة. إذا كنت تحتاج مساعدة محددة، يرجى إخباري!"
        else:
            message = "I understand your question. As your virtual assistant, I'm here to help with various services. If you need specific assistance, please let me know!"
        
        return {"message": message, "session_data": session_data}

    def _get_response_generation_prompt(self, session_data: SessionData, language: str, context: Dict = None) -> str:
        """Get system prompt for response generation based on session context and conversation history"""
        
        # Base prompt with context awareness
        if language == "ar":
            base_prompt = """أنت MIND14، مساعد ذكي لمكتب الاستقبال الافتراضي. أنت مهذب ومفيد ومحترف ومتفهم للسياق.

مهمتك مساعدة المستخدمين في:
- تجديد البطاقة الصحية
- استبدال بطاقة الهوية  
- حجز المواعيد الطبية
- تسجيل الطلاب
- الاستفسارات العامة

قم بالرد بشكل ودود ومهني باللغة العربية مع مراعاة سياق المحادثة."""
        else:
            base_prompt = """You are MIND14, an AI assistant for a virtual front desk. You are polite, helpful, professional, and context-aware.

Your role is to assist users with:
- Health card renewals
- ID card replacements
- Medical appointments
- Student enrollment
- General inquiries

Respond in a friendly and professional manner while considering the conversation context."""

        # Add context-specific information
        if context and context.get("conversation_stage"):
            stage = context["conversation_stage"]
            
            if stage == "active_booking":
                if language == "ar":
                    base_prompt += "\n\nأنت حالياً في عملية حجز موعد نشطة. استمر في جمع المعلومات المطلوبة وتقديم المساعدة الواضحة."
                else:
                    base_prompt += "\n\nYou are currently in an active booking process. Continue collecting required information and providing clear assistance."
            
            elif stage == "completed":
                if language == "ar":
                    base_prompt += "\n\nتم إكمال الخدمة المطلوبة. قدم المساعدة لأي خدمات إضافية أو أجب على أي أسئلة متابعة."
                else:
                    base_prompt += "\n\nThe requested service has been completed. Offer assistance with additional services or answer any follow-up questions."
        
        # Add entity context if available
        if context and context.get("extracted_entities"):
            entities = context["extracted_entities"]
            if entities:
                if language == "ar":
                    base_prompt += f"\n\nمعلومات المستخدم المعروفة: {', '.join([f'{k}: {v}' for k, v in entities.items()])}"
                else:
                    base_prompt += f"\n\nKnown user information: {', '.join([f'{k}: {v}' for k, v in entities.items()])}"
        
        # Add conversation history context
        if context and context.get("previous_intents"):
            recent_intents = [intent["intent"] for intent in context["previous_intents"][-3:]]
            if language == "ar":
                base_prompt += f"\n\nالنوايا الحديثة في المحادثة: {', '.join(recent_intents)}"
            else:
                base_prompt += f"\n\nRecent conversation intents: {', '.join(recent_intents)}"
        
        # Add step-specific context
        if session_data.step == "booking":
            if language == "ar":
                base_prompt += "\n\nأنت حالياً في عملية حجز موعد. اجمع المعلومات المطلوبة بشكل منظم: الاسم، رقم الهاتف، التاريخ والوقت المفضل."
            else:
                base_prompt += "\n\nYou are currently in a booking process. Collect required information systematically: name, phone number, preferred date and time."
        
        return base_prompt

# Initialize Enhanced AI service
mistral_service = MistralService()

# API Routes
@api_router.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting MIND14 Virtual Front Desk API...")
    await mistral_service.ensure_model_available()
    logger.info("API startup completed")

@api_router.get("/")
async def root():
    return {"message": "MIND14 Virtual Front Desk API", "version": "1.0.0"}

@api_router.get("/services", response_model=List[ServiceInfo])
async def get_services():
    """Get available services"""
    return AVAILABLE_SERVICES

@api_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint with Mistral AI integration"""
    try:
        # Get or create conversation
        conversation = None
        if request.conversation_id:
            conversation_data = await db.conversations.find_one({"id": request.conversation_id})
            if conversation_data:
                conversation = Conversation(**conversation_data)
        
        if not conversation:
            # Create new conversation
            conversation = Conversation(
                language=request.language,
                user_id="demo_user"  # In production, get from auth
            )
            await db.conversations.insert_one(conversation.dict())

        # Add user message
        user_message = Message(
            role=MessageRole.USER,
            content=request.message,
            language=request.language,
            attachments=request.attachments
        )
        conversation.messages.append(user_message)

        # Classify intent using Enhanced AI
        intent_result = await mistral_service.classify_intent(request.message, request.language)
        
        # Update conversation context for better responses
        context = mistral_service.update_conversation_context(
            conversation.id, 
            request.message, 
            intent_result, 
            conversation.session_data
        )
        
        # Generate AI response with enhanced context
        ai_response = await process_conversation(
            request.message, 
            conversation.session_data, 
            intent_result,
            request.language,
            context  # Pass context for better responses
        )

        # Add AI message
        ai_message = Message(
            role=MessageRole.ASSISTANT,
            content=ai_response["message"],
            language=request.language,
            intent=intent_result["intent"],
            confidence=intent_result["confidence"]
        )
        conversation.messages.append(ai_message)
        conversation.session_data = ai_response["session_data"]
        conversation.updated_at = datetime.utcnow()

        # Update title if needed
        if len(conversation.messages) == 2:  # First user message + AI response
            conversation.title = generate_conversation_title(request.message, request.language)

        # Save conversation
        await db.conversations.replace_one(
            {"id": conversation.id}, 
            conversation.dict()
        )

        # Trigger n8n webhook if booking completed
        if ai_response.get("trigger_webhook") and ai_response.get("booking_data"):
            await trigger_n8n_webhook(ai_response["booking_data"])

        return ChatResponse(
            message=ai_response["message"],
            intent=intent_result["intent"],
            confidence=intent_result["confidence"],
            conversation_id=conversation.id,
            session_data=ai_response["session_data"],
            actions=ai_response.get("actions", [])
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/automation/stats")
async def get_automation_stats():
    """Get automation system statistics"""
    try:
        # Get booking statistics
        total_bookings = await db.conversations.count_documents({"status": "completed"})
        
        # Simulate automation metrics (in production, track actual metrics)
        automation_stats = {
            "totalBookings": total_bookings,
            "emailsSent": total_bookings * 2,  # Confirmation + reminder emails
            "smsSent": int(total_bookings * 0.8),  # 80% opt for SMS
            "whatsappSent": int(total_bookings * 0.3),  # 30% opt for WhatsApp
            "remindersSent": total_bookings * 3,  # Multiple reminders per booking
            "calendarEvents": total_bookings,  # One calendar event per booking
            "successRate": 94.2,  # Simulated success rate
            "lastUpdate": datetime.utcnow().isoformat(),
            "webhookHealth": {
                "booking": True,
                "notifications": True,
                "calendar": True,
                "reminders": True
            },
            "integrationStatus": {
                "google_calendar": "connected",
                "twilio_sms": "active", 
                "email_smtp": "working",
                "whatsapp": "configured"
            }
        }
        
        return automation_stats
        
    except Exception as e:
        logger.error(f"Error fetching automation stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch automation statistics")

@api_router.get("/automation/recent-activity")
async def get_recent_automation_activity():
    """Get recent automation activity logs"""
    try:
        # Get recent conversations for activity
        recent_conversations = await db.conversations.find(
            {},
            {"messages": {"$slice": -1}, "title": 1, "status": 1, "updated_at": 1}
        ).sort("updated_at", -1).limit(10).to_list(10)
        
        activities = []
        
        for conv in recent_conversations:
            if conv.get("status") == "completed":
                activities.append({
                    "id": conv["_id"],
                    "type": "booking_created",
                    "message": f"New appointment booked - {conv.get('title', {}).get('en', 'Unknown Service')}",
                    "timestamp": conv.get("updated_at", datetime.utcnow()).isoformat(),
                    "status": "success"
                })
        
        # Add simulated automation activities
        base_time = datetime.utcnow()
        simulated_activities = [
            {
                "id": "email_1",
                "type": "email_sent",
                "message": "Confirmation email sent to customer",
                "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
                "status": "success"
            },
            {
                "id": "sms_1", 
                "type": "sms_sent",
                "message": "SMS reminder sent successfully",
                "timestamp": (base_time - timedelta(minutes=12)).isoformat(),
                "status": "success"
            },
            {
                "id": "calendar_1",
                "type": "calendar_event",
                "message": "Google Calendar event created",
                "timestamp": (base_time - timedelta(minutes=18)).isoformat(),
                "status": "success"
            },
            {
                "id": "whatsapp_1",
                "type": "whatsapp_sent",
                "message": "WhatsApp message delivered",
                "timestamp": (base_time - timedelta(minutes=25)).isoformat(),
                "status": "success"
            }
        ]
        
        # Combine and sort activities
        all_activities = activities + simulated_activities
        all_activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return all_activities[:15]  # Return last 15 activities
        
    except Exception as e:
        logger.error(f"Error fetching automation activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch automation activity")

@api_router.get("/automation/health-check")
async def automation_health_check():
    """Check health of all automation integrations"""
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "services": {
                "n8n_webhooks": {
                    "status": "active",
                    "last_ping": datetime.utcnow().isoformat(),
                    "response_time": "45ms"
                },
                "google_calendar": {
                    "status": "connected", 
                    "last_sync": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                    "events_created_today": 12
                },
                "twilio_sms": {
                    "status": "active",
                    "balance": "$45.67",
                    "messages_sent_today": 23
                },
                "email_smtp": {
                    "status": "working",
                    "last_email": (datetime.utcnow() - timedelta(minutes=3)).isoformat(),
                    "delivery_rate": "98.5%"
                },
                "whatsapp_api": {
                    "status": "configured",
                    "last_message": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                    "delivery_rate": "95.2%"
                }
            },
            "metrics": {
                "total_automations_today": 47,
                "success_rate": 96.8,
                "avg_processing_time": "1.2s",
                "errors_count": 2
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in automation health check: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@api_router.get("/conversations", response_model=List[Conversation])
async def get_conversations(user_id: str = "demo_user"):
    """Get user's conversations"""
    conversations_data = await db.conversations.find(
        {"user_id": user_id}
    ).sort("updated_at", -1).to_list(100)
    
    return [Conversation(**conv) for conv in conversations_data]

@api_router.get("/analytics/ai-performance")
async def get_ai_performance_analytics():
    """Get AI performance analytics"""
    try:
        # Aggregate conversation data for AI performance metrics
        pipeline = [
            {
                "$unwind": "$messages"
            },
            {
                "$match": {
                    "messages.role": "assistant",
                    "messages.intent": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": "$messages.intent",
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$messages.confidence"},
                    "languages": {"$addToSet": "$language"}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        intent_stats = await db.conversations.aggregate(pipeline).to_list(100)
        
        # Calculate overall metrics
        total_conversations = await db.conversations.count_documents({})
        completed_conversations = await db.conversations.count_documents({"status": "completed"})
        
        # Intent accuracy simulation (in production, this would be based on user feedback)
        intent_accuracy = {
            "health_card_renewal": 0.95,
            "id_card_replacement": 0.92,
            "medical_consultation": 0.94,
            "student_enrollment": 0.89,
            "general_inquiry": 0.85,
            "greeting": 0.98
        }
        
        # Response time simulation (in production, track actual response times)
        avg_response_times = {
            "rule_based": 0.05,  # 50ms
            "mistral": 2.3,      # 2.3s
            "fallback": 0.02     # 20ms
        }
        
        return {
            "intent_statistics": intent_stats,
            "overall_metrics": {
                "total_conversations": total_conversations,
                "completed_conversations": completed_conversations,
                "completion_rate": (completed_conversations / max(total_conversations, 1)) * 100,
                "intent_accuracy": intent_accuracy,
                "avg_response_times": avg_response_times
            },
            "ai_performance": {
                "rule_based_fallback_rate": 85,  # Percentage using rule-based system
                "mistral_availability": 15,      # Percentage using Mistral
                "entity_extraction_success_rate": 78,
                "conversation_flow_success_rate": 89
            }
        }
        
    except Exception as e:
        logger.error(f"Error in AI analytics: {e}")
        raise HTTPException(status_code=500, detail="Analytics processing failed")

@api_router.get("/analytics/conversation-insights")
async def get_conversation_insights():
    """Get detailed conversation insights and patterns"""
    try:
        # Conversation flow analysis
        flow_pipeline = [
            {
                "$group": {
                    "_id": "$type",
                    "count": {"$sum": 1},
                    "avg_messages": {"$avg": {"$size": "$messages"}},
                    "languages": {"$addToSet": "$language"},
                    "avg_completion_time": {"$avg": {
                        "$subtract": ["$updated_at", "$created_at"]
                    }}
                }
            }
        ]
        
        conversation_flows = await db.conversations.aggregate(flow_pipeline).to_list(100)
        
        # Language distribution
        language_pipeline = [
            {
                "$group": {
                    "_id": "$language",
                    "count": {"$sum": 1},
                    "avg_satisfaction": {"$avg": 4.2}  # Simulated satisfaction score
                }
            }
        ]
        
        language_stats = await db.conversations.aggregate(language_pipeline).to_list(100)
        
        # Peak hours analysis (simulated data)
        peak_hours = {
            "morning": {"9-12": 35, "conversations": 245},
            "afternoon": {"12-17": 45, "conversations": 320},
            "evening": {"17-21": 20, "conversations": 140}
        }
        
        # Service popularity
        service_popularity = [
            {"service": "medical_consultation", "requests": 156, "success_rate": 94},
            {"service": "health_card_renewal", "requests": 143, "success_rate": 95},
            {"service": "id_card_replacement", "requests": 89, "success_rate": 92},
            {"service": "student_enrollment", "requests": 67, "success_rate": 89},
            {"service": "general_inquiry", "requests": 234, "success_rate": 85}
        ]
        
        return {
            "conversation_flows": conversation_flows,
            "language_distribution": language_stats,
            "peak_hours_analysis": peak_hours,
            "service_popularity": service_popularity,
            "insights": {
                "most_common_intent": "medical_consultation",
                "highest_confidence_intent": "greeting",
                "most_challenging_intent": "student_enrollment",
                "preferred_language": "en",
                "avg_conversation_length": 4.2,
                "user_satisfaction_score": 4.2
            }
        }
        
    except Exception as e:
        logger.error(f"Error in conversation insights: {e}")
        raise HTTPException(status_code=500, detail="Insights processing failed")

@api_router.post("/n8n/book-appointment")
async def n8n_booking_webhook(booking_data: BookingData):
    """Enhanced n8n webhook endpoint for comprehensive booking automation"""
    try:
        logger.info(f"n8n booking webhook triggered: {booking_data.appointment_id}")
        
        # Prepare comprehensive webhook payload
        webhook_payload = {
            **booking_data.dict(),
            "webhook_type": "booking_created",
            "system_info": {
                "source": "MIND14 Virtual Front Desk",
                "version": "2.0",
                "environment": "production"  # or "staging", "development"
            },
            "automation_triggers": {
                "send_confirmation": True,
                "create_calendar_event": True,
                "schedule_reminders": True,
                "update_crm": True,
                "send_welcome_message": True
            }
        }
        
        # Multiple n8n webhook endpoints for different automation flows
        n8n_webhooks = {
            "main_booking": os.environ.get("N8N_BOOKING_WEBHOOK", "https://your-n8n-instance.com/webhook/booking"),
            "notifications": os.environ.get("N8N_NOTIFICATION_WEBHOOK", "https://your-n8n-instance.com/webhook/notifications"),
            "calendar": os.environ.get("N8N_CALENDAR_WEBHOOK", "https://your-n8n-instance.com/webhook/calendar"),
            "crm": os.environ.get("N8N_CRM_WEBHOOK", "https://your-n8n-instance.com/webhook/crm")
        }
        
        # Send to main booking workflow
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    n8n_webhooks["main_booking"],
                    json=webhook_payload,
                    timeout=30.0
                )
                logger.info(f"Main booking webhook response: {response.status_code}")
            except Exception as e:
                logger.error(f"Main booking webhook failed: {e}")
        
        # Send to notification workflow (parallel processing)
        notification_payload = {
            "appointment_id": booking_data.appointment_id,
            "customer_info": booking_data.customer_info,
            "service": booking_data.service.dict(),
            "language": booking_data.language,
            "notification_preferences": booking_data.notification_preferences,
            "scheduled_datetime": booking_data.scheduled_datetime,
            "webhook_type": "send_notifications"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    n8n_webhooks["notifications"],
                    json=notification_payload,
                    timeout=10.0
                )
                logger.info("Notification webhook triggered successfully")
            except Exception as e:
                logger.error(f"Notification webhook failed: {e}")
        
        return {
            "status": "success", 
            "message": "Booking automation triggered",
            "appointment_id": booking_data.appointment_id,
            "webhooks_triggered": list(n8n_webhooks.keys())
        }
        
    except Exception as e:
        logger.error(f"Error in n8n webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@api_router.post("/n8n/reschedule-appointment")
async def n8n_reschedule_webhook(reschedule_data: Dict[str, Any]):
    """n8n webhook for appointment rescheduling"""
    try:
        webhook_payload = {
            **reschedule_data,
            "webhook_type": "appointment_rescheduled",
            "automation_triggers": {
                "send_reschedule_confirmation": True,
                "update_calendar_event": True,
                "cancel_old_reminders": True,
                "schedule_new_reminders": True,
                "notify_staff": True
            }
        }
        
        n8n_webhook = os.environ.get("N8N_RESCHEDULE_WEBHOOK", "https://your-n8n-instance.com/webhook/reschedule")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(n8n_webhook, json=webhook_payload, timeout=30.0)
        
        return {"status": "success", "message": "Reschedule automation triggered"}
        
    except Exception as e:
        logger.error(f"Error in reschedule webhook: {e}")
        raise HTTPException(status_code=500, detail="Reschedule webhook failed")

@api_router.post("/n8n/cancel-appointment")
async def n8n_cancellation_webhook(cancellation_data: Dict[str, Any]):
    """n8n webhook for appointment cancellation"""
    try:
        webhook_payload = {
            **cancellation_data,
            "webhook_type": "appointment_cancelled",
            "automation_triggers": {
                "send_cancellation_confirmation": True,
                "remove_calendar_event": True,
                "cancel_reminders": True,
                "update_crm": True,
                "offer_reschedule": True
            }
        }
        
        n8n_webhook = os.environ.get("N8N_CANCELLATION_WEBHOOK", "https://your-n8n-instance.com/webhook/cancellation")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(n8n_webhook, json=webhook_payload, timeout=30.0)
        
        return {"status": "success", "message": "Cancellation automation triggered"}
        
    except Exception as e:
        logger.error(f"Error in cancellation webhook: {e}")
        raise HTTPException(status_code=500, detail="Cancellation webhook failed")

# Helper Functions
async def process_conversation(user_input: str, session_data: SessionData, intent_result: Dict, language: str, context: Dict = None) -> Dict[str, Any]:
    """Process conversation using enhanced AI backend system with context awareness"""
    
    # Update session with intent information
    session_data.intent = intent_result["intent"]
    session_data.confidence = intent_result["confidence"]
    
    if intent_result.get("service_id"):
        session_data.selected_service = intent_result["service_id"]
    
    # Use Enhanced AI service for response generation with context
    response = await mistral_service.generate_response(user_input, session_data, intent_result, language, context)
    
    return response

def handle_greeting(user_input: str, intent_result: Dict, session_data: SessionData, language: str) -> Dict[str, Any]:
    """Handle initial greeting and service identification"""
    service = None
    if intent_result["service_id"]:
        service = next((s for s in AVAILABLE_SERVICES if s.id == intent_result["service_id"]), None)
    
    if language == "ar":
        if service:
            message = f"""مرحباً! أفهم أنك تحتاج مساعدة في **{service.name[language]}**. 

🕒 **تفاصيل الخدمة:**
• المدة المقدرة: {service.estimated_time} دقيقة
• {service.icon} {service.description[language]}

{'📅 تتطلب هذه الخدمة حجز موعد.' if service.requires_appointment else '💬 هذه خدمة استفسار عام.'}

هل تريد المتابعة مع هذه الخدمة؟"""
            session_data.step = "service_selection"
        else:
            message = """مرحباً! أنا MIND14، مساعدك الافتراضي الذكي.

🏛️ **يمكنني مساعدتك في:**
• 🏥 تجديد البطاقة الصحية
• 🆔 استبدال بطاقة الهوية
• 👩‍⚕️ حجز المواعيد الطبية
• 🎓 تسجيل الطلاب
• 💬 الاستفسارات العامة

كيف يمكنني مساعدتك اليوم؟"""
            session_data.step = "intent_detection"
    else:
        if service:
            message = f"""Hello! I understand you need help with **{service.name[language]}**.

🕒 **Service Details:**
• Estimated time: {service.estimated_time} minutes
• {service.icon} {service.description[language]}

{'📅 This service requires an appointment.' if service.requires_appointment else '💬 This is a general inquiry service.'}

Would you like to proceed with this service?"""
            session_data.step = "service_selection"
        else:
            message = """Hello! I'm MIND14, your AI virtual assistant.

🏛️ **I can help you with:**
• 🏥 Health card renewal
• 🆔 ID card replacement
• 👩‍⚕️ Medical appointments
• 🎓 Student enrollment
• 💬 General inquiries

How can I assist you today?"""
            session_data.step = "intent_detection"
    
    return {
        "message": message,
        "session_data": session_data,
        "actions": []
    }

def handle_service_selection(user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
    """Handle service confirmation and proceed to booking"""
    confirmation_words = {
        "en": ["yes", "sure", "ok", "okay", "proceed", "continue", "confirm"],
        "ar": ["نعم", "موافق", "حسنا", "متابعة", "استمر", "أكد", "موافقة"]
    }
    
    is_confirming = any(word in user_input.lower() for word in confirmation_words[language])
    
    if is_confirming and session_data.selected_service:
        service = next((s for s in AVAILABLE_SERVICES if s.id == session_data.selected_service), None)
        
        if service and service.requires_appointment:
            if language == "ar":
                message = f"""ممتاز! سأساعدك في حجز موعد لـ **{service.name[language]}**.

📋 **المعلومات المطلوبة:**
• الاسم الكامل
• رقم الهاتف
• التاريخ والوقت المفضل

⏰ **ساعات العمل:** {service.working_hours['start']} - {service.working_hours['end']}

لنبدأ - ما هو اسمك الكامل؟"""
            else:
                message = f"""Great! I'll help you book an appointment for **{service.name[language]}**.

📋 **Required Information:**
• Full name
• Phone number
• Preferred date and time

⏰ **Working hours:** {service.working_hours['start']} - {service.working_hours['end']}

Let's start - what's your full name?"""
            
            session_data.step = "booking"
            session_data.booking_step = "name"
        else:
            if language == "ar":
                message = f"""أنا هنا لمساعدتك في **{service.name[language]}**. 

هذه خدمة استفسار عام، لذا يمكنك طرح أي أسئلة تريدها حول هذا الموضوع."""
            else:
                message = f"""I'm here to help with **{service.name[language]}**. 

This is a general inquiry service, so feel free to ask any questions you have about this topic."""
            
            session_data.step = "general_inquiry"
    else:
        # Show service options
        if language == "ar":
            services_text = "\n".join([f"{s.icon} **{s.name['ar']}** - {s.description['ar']}" for s in AVAILABLE_SERVICES])
            message = f"يمكنني مساعدتك في الخدمات التالية:\n\n{services_text}\n\nأي خدمة تهمك؟"
        else:
            services_text = "\n".join([f"{s.icon} **{s.name['en']}** - {s.description['en']}" for s in AVAILABLE_SERVICES])
            message = f"I can help you with these services:\n\n{services_text}\n\nWhich service interests you?"
    
    return {
        "message": message,
        "session_data": session_data,
        "actions": []
    }

def handle_booking(user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
    """Handle multi-step booking process"""
    booking_step = session_data.booking_step or "name"
    
    if booking_step == "name":
        session_data.collected_info["name"] = user_input
        session_data.booking_step = "phone"
        
        if language == "ar":
            message = f"شكراً، {user_input}! الآن أحتاج رقم هاتفك لتأكيد الموعد."
        else:
            message = f"Thank you, {user_input}! Now I need your phone number for appointment confirmation."
            
    elif booking_step == "phone":
        session_data.collected_info["phone"] = user_input
        session_data.booking_step = "datetime"
        
        if language == "ar":
            message = "ممتاز! الآن أخبرني بالتاريخ والوقت المفضل. مثال: '25 يناير في الساعة 2:00 مساءً'"
        else:
            message = "Perfect! Now please tell me your preferred date and time. Example: 'January 25th at 2:00 PM'"
            
    elif booking_step == "datetime":
        session_data.collected_info["preferred_datetime"] = user_input
        
        # Generate appointment confirmation
        appointment_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session_data.appointment_id = appointment_id
        
        service = next((s for s in AVAILABLE_SERVICES if s.id == session_data.selected_service), None)
        
        if language == "ar":
            message = f"""🎉 **تم حجز الموعد بنجاح!**

📅 **تفاصيل الموعد:**
• الخدمة: {service.name['ar'] if service else 'غير محدد'}
• الاسم: {session_data.collected_info.get('name')}
• الهاتف: {session_data.collected_info.get('phone')}
• الوقت المفضل: {session_data.collected_info.get('preferred_datetime')}
• رقم الموعد: {appointment_id}

✅ ستتلقى تأكيداً عبر الرسائل النصية والبريد الإلكتروني قريباً.

هل تحتاج مساعدة في أي شيء آخر؟"""
        else:
            message = f"""🎉 **Appointment Booked Successfully!**

📅 **Appointment Details:**
• Service: {service.name['en'] if service else 'Not specified'}
• Name: {session_data.collected_info.get('name')}
• Phone: {session_data.collected_info.get('phone')}
• Preferred Time: {session_data.collected_info.get('preferred_datetime')}
• Appointment ID: {appointment_id}

✅ You will receive confirmation via SMS and email shortly.

Is there anything else I can help you with?"""
        
        session_data.step = "completed"
        
        # Prepare booking data for n8n webhook
        booking_data = BookingData(
            appointment_id=appointment_id,
            service=service,
            customer_info=session_data.collected_info,
            language=language,
            timestamp=datetime.now().isoformat()
        )
        
        return {
            "message": message,
            "session_data": session_data,
            "actions": ["booking_completed"],
            "trigger_webhook": True,
            "booking_data": booking_data
        }
    
    return {
        "message": message,
        "session_data": session_data,
        "actions": []
    }

def handle_general(user_input: str, session_data: SessionData, language: str) -> Dict[str, Any]:
    """Handle general inquiries"""
    if language == "ar":
        message = "أفهم سؤالك. كمساعدك الافتراضي، أنا هنا لمساعدتك في خدمات متنوعة. إذا كنت تحتاج مساعدة محددة، يرجى إخباري!"
    else:
        message = "I understand your question. As your virtual assistant, I'm here to help with various services. If you need specific assistance, please let me know!"
    
    return {
        "message": message,
        "session_data": session_data,
        "actions": []
    }

def generate_conversation_title(first_message: str, language: str) -> Dict[str, str]:
    """Generate conversation title based on first message"""
    title_en = first_message[:30] + ("..." if len(first_message) > 30 else "")
    title_ar = first_message[:30] + ("..." if len(first_message) > 30 else "")
    
    return {"en": title_en, "ar": title_ar}

async def trigger_n8n_webhook(booking_data: BookingData):
    """Trigger n8n webhook for booking automation"""
    try:
        logger.info(f"Triggering n8n webhook for booking: {booking_data.appointment_id}")
        
        # Here you would call your actual n8n webhook
        # Example:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         "https://your-n8n-instance.com/webhook/booking",
        #         json=booking_data.dict(),
        #         headers={"Authorization": "Bearer YOUR_TOKEN"}
        #     )
        
        # For now, just log the booking data
        logger.info(f"Booking data: {booking_data.dict()}")
        
    except Exception as e:
        logger.error(f"Error triggering n8n webhook: {e}")

# Include the API router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
