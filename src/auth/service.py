"""
Authentication and Authorization Service
Handles user authentication, JWT tokens, and rate limiting
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import BaseModel, ValidationError
from jose import JWTError, jwt
from jose.exceptions import JWTError

# Configuration
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "user:read": "Read access to user data",
        "user:write": "Write access to user data",
        "code:read": "Read access to code",
        "code:write": "Write access to code",
        "admin": "Admin access"
    }
)

class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str

class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    scopes: List[str] = []

class User(BaseModel):
    """User model"""
    user_id: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: List[str] = []
    rate_limit: int = 100  # Requests per minute

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Try again in {retry_after} seconds.")

class AuthService:
    """Handles authentication and authorization"""
    
    def __init__(self):
        self.rate_limits: Dict[str, List[float]] = {}
        self.users_db: Dict[str, User] = self._load_users()
    
    def _load_users(self) -> Dict[str, User]:
        """Load users from environment or database"""
        # In a real application, this would query a database
        # For now, we'll use a simple in-memory dictionary
        return {
            "user1@example.com": User(
                user_id="user1",
                email="user1@example.com",
                full_name="Test User",
                scopes=["user:read", "code:read"],
                rate_limit=100
            ),
            "admin@example.com": User(
                user_id="admin",
                email="admin@example.com",
                full_name="Admin User",
                scopes=["admin"],
                rate_limit=1000
            )
        }
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def get_user(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.users_db.get(email)
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        # In a real application, you would validate against a database
        user = self.get_user(email)
        if not user:
            return None
        if not self.verify_password(password, "hashed_password_in_db"):  # Replace with actual hash check
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, data: dict) -> str:
        """Create a refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    async def get_current_user(
        self,
        security_scopes: SecurityScopes,
        token: str = Depends(oauth2_scheme)
    ) -> User:
        """Get the current authenticated user"""
        if security_scopes.scopes:
            authenticate_value = f'Bearer scope=\"{security_scopes.scope_str}"'
        else:
            authenticate_value = "Bearer"
        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
            token_scopes = payload.get("scopes", [])
            token_data = TokenData(user_id=user_id, scopes=token_scopes)
        except (JWTError, ValidationError):
            raise credentials_exception
        
        user = self.get_user(token_data.user_id)
        if user is None:
            raise credentials_exception
        
        # Check scopes
        if security_scopes.scopes:
            for scope in security_scopes.scopes:
                if scope not in token_data.scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions",
                        headers={"WWW-Authenticate": authenticate_value},
                    )
        
        return user
    
    def check_rate_limit(self, user: User) -> None:
        """Check and update rate limit for a user"""
        now = time.time()
        user_requests = self.rate_limits.get(user.user_id, [])
        
        # Remove requests older than 1 minute
        recent_requests = [t for t in user_requests if now - t < 60]
        
        if len(recent_requests) >= user.rate_limit:
            # Calculate when the oldest request will be older than 1 minute
            retry_after = int(60 - (now - recent_requests[0]))
            raise RateLimitExceeded(retry_after=retry_after)
        
        # Add current request
        recent_requests.append(now)
        self.rate_limits[user.user_id] = recent_requests

# Singleton instance
auth_service = AuthService()

# Dependencies
get_current_active_user = auth_service.get_current_user

# Rate limiting middleware
async def rate_limiter(user: User = Depends(get_current_active_user)):
    """Dependency to check rate limits"""
    auth_service.check_rate_limit(user)
    return user
