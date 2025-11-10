"""
Authentication API Endpoints
Handles user authentication, token management, and password reset
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from ...auth.service import (
    auth_service,
    Token,
    User,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    RateLimitExceeded
)

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model"""
    email: str
    password: str

class TokenResponse(Token):
    """Token response model"""
    user_id: str
    email: str
    full_name: Optional[str] = None
    scopes: list[str] = []

class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str
    new_password: str

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2 compatible token login, get an access token for future requests"""
    try:
        # Check rate limiting first
        client_ip = request.client.host
        auth_service.check_rate_limit(User(user_id=client_ip, email=client_ip, scopes=[]))
        
        # Authenticate user
        user = auth_service.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.email, "scopes": user.scopes},
            expires_delta=access_token_expires
        )
        refresh_token = auth_service.create_refresh_token(
            data={"sub": user.email}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "refresh_token": refresh_token,
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "scopes": user.scopes
        }
        
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_token: str
):
    """Refresh an access token using a refresh token"""
    try:
        # Verify refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                auth_service.SECRET_KEY,
                algorithms=[auth_service.ALGORITHM]
            )
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            user_email = payload.get("sub")
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Get user
            user = auth_service.get_user(user_email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Create new access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            new_access_token = auth_service.create_access_token(
                data={"sub": user.email, "scopes": user.scopes},
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds()),
                "refresh_token": refresh_token,
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "scopes": user.scopes
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except (jwt.JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refreshing token"
        )

@router.post("/password/reset/request")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    request: Request
):
    """Request a password reset email"""
    try:
        # In a real application, you would:
        # 1. Check if the email exists
        # 2. Generate a reset token
        # 3. Send an email with the reset link
        
        # For demo purposes, we'll just log the request
        reset_token = auth_service.create_access_token(
            data={"sub": reset_request.email},
            expires_delta=timedelta(hours=1)
        )
        
        reset_url = f"{request.base_url}auth/password/reset/confirm?token={reset_token}"
        logger.info(f"Password reset requested for {reset_request.email}. Reset URL: {reset_url}")
        
        return {"message": "If your email exists in our system, you will receive a password reset link"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password reset request"
        )

@router.post("/password/reset/confirm")
async def confirm_password_reset(confirm: PasswordResetConfirm):
    """Confirm password reset with a valid token"""
    try:
        # Verify the reset token
        try:
            payload = jwt.decode(
                confirm.token,
                auth_service.SECRET_KEY,
                algorithms=[auth_service.ALGORITHM]
            )
            user_email = payload.get("sub")
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token"
                )
            
            # In a real application, you would:
            # 1. Update the user's password in the database
            # 2. Invalidate the reset token
            # 3. Send a confirmation email
            
            logger.info(f"Password reset for {user_email} was successful")
            return {"message": "Password has been reset successfully"}
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        except (jwt.JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password"
        )

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(auth_service.get_current_active_user)):
    """Get current user information"""
    return current_user
