"""
Pydantic validators for Google Play billing endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class VerifyPurchaseRequest(BaseModel):
    """Request to verify a Google Play purchase"""
    product_id: str = Field(..., description="Google Play product SKU")
    purchase_token: str = Field(..., description="Google Play purchase token")
    product_type: Literal['subscription', 'product'] = Field(..., description="Type of purchase")


class VerifyPurchaseResponse(BaseModel):
    """Response from purchase verification"""
    success: bool
    is_valid: bool
    purchase_id: Optional[int] = None
    error: Optional[str] = None
    message: str


class ProcessPurchaseRequest(BaseModel):
    """Request to process a verified purchase"""
    purchase_id: int = Field(..., description="Database purchase ID from verification step")


class ProcessPurchaseResponse(BaseModel):
    """Response from processing a purchase"""
    success: bool
    old_subscription: Optional[int] = None
    new_subscription: Optional[int] = None
    old_credits: Optional[int] = None
    new_credits: Optional[int] = None
    credits_granted: int
    message: str
    error: Optional[str] = None


class GooglePlayWebhookRequest(BaseModel):
    """Google Play Real-time Developer Notification"""
    version: str
    packageName: str
    eventTimeMillis: str
    subscriptionNotification: Optional[dict] = None
    oneTimeProductNotification: Optional[dict] = None


class UpdateSubscriptionRequest(BaseModel):
    """Admin request to manually update user subscription"""
    subscription_level: int = Field(..., ge=0, le=10, description="New subscription level (0=free, 2=premium, 3=family)")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for subscription change")


class UpdateSubscriptionResponse(BaseModel):
    """Response from manual subscription update"""
    success: bool
    uid: str
    old_subscription: int
    new_subscription: int
    message: str


class GetPurchaseHistoryResponse(BaseModel):
    """Response containing user's purchase history"""
    purchases: list
    count: int


class RefundPurchaseRequest(BaseModel):
    """Admin request to refund a purchase"""
    purchase_id: int = Field(..., description="Database purchase ID to refund")
    refund_reason: str = Field(..., min_length=3, max_length=500, description="Reason for refund")
    admin_key: str = Field(..., description="Admin authorization key")


class RefundPurchaseResponse(BaseModel):
    """Response from refund operation"""
    success: bool
    purchase_id: int
    product_id: str
    credits_deducted: int
    old_credits: int
    new_credits: int
    message: str
    error: Optional[str] = None
