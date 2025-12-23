"""
CRM Domain Entities
"""

from enum import Enum


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class LeadSource(str, Enum):
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    PHONE = "phone"
    EVENT = "event"
    OTHER = "other"


class OpportunityStage(str, Enum):
    QUALIFICATION = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"
    OTHER = "other"


class ActivityStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"
