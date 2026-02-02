from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class EncryptedPayload(BaseModel):
    ciphertext: str  # Base64 encoded AES-GCM
    iv: str          # Base64 encoded nonce
    tag: str         # Base64 encoded auth tag

class SignalingMessage(BaseModel):
    type: str  # 'offer', 'answer', 'ice_candidate', 'call_invite', 'call_reject'
    from_user: str = Field(..., alias="from")
    to_user: str = Field(..., alias="to")
    ephemeral_key: Optional[str] = None  # Base64 X25519 public key (sent with invite/answer)
    payload: Optional[Dict[str, Any]] = None
    
    class Config:
        allow_population_by_field_name = True

class RegistrationMessage(BaseModel):
    user_id: str
    public_identity_key: str  # Base64 X25519 long-term identity key
