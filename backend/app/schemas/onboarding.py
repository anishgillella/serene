from pydantic import BaseModel
from typing import List, Optional, Literal

class PartnerProfileInput(BaseModel):
    name: str
    role: Literal["boyfriend", "girlfriend", "partner_a", "partner_b"]
    age: Optional[int] = None
    communication_style: str
    stress_triggers: List[str]
    soothing_mechanisms: List[str]
    background_story: Optional[str] = None
    
    # New detailed fields
    hobbies: List[str] = []
    favorite_food: Optional[str] = None
    favorite_cuisine: Optional[str] = None
    favorite_sports: List[str] = []
    favorite_books: List[str] = []
    favorite_celebrities: List[str] = []
    traumatic_experiences: Optional[str] = None
    key_life_experiences: Optional[str] = None
    
    # Perspective on partner
    partner_description: Optional[str] = None
    what_i_admire: Optional[str] = None
    what_frustrates_me: Optional[str] = None

class RelationshipProfileInput(BaseModel):
    recurring_arguments: List[str]
    shared_goals: List[str]
    relationship_dynamic: Optional[str] = None

class OnboardingSubmission(BaseModel):
    relationship_id: str
    partner_id: str
    partner_profile: PartnerProfileInput
    relationship_profile: RelationshipProfileInput

class OnboardingResponse(BaseModel):
    success: bool
    message: str
    profile_id: Optional[str] = None
