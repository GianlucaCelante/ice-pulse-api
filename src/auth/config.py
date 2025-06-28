# =====================================================
# src/auth/config.py - FastAPI-Users Configuration  
# =====================================================
import os
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Request, Response
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,  # FIX: Era JWTAuthentication, ora è JWTStrategy
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import InvalidPasswordException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User  # ✅ User model ora FastAPI-Users compatible
from src.database.connection import get_db

# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================

# JWT Secret - SICURO per production
JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("JWT_SECRET environment variable must be set in production")
    else:
        # Solo per development - genera warning
        JWT_SECRET = "dev-secret-key-change-in-production"
        print("⚠️  WARNING: Using default JWT secret for development only!")
JWT_SECRET_STR: str = str(JWT_SECRET)

JWT_ALGORITHM = "HS256"

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minuti per access token

# =====================================================
# TRANSPORT & AUTHENTICATION SETUP
# =====================================================

# Bearer token transport (Authorization: Bearer <token>)
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# JWT Strategy (FIX: Nuovo modo FastAPI-Users)
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=JWT_SECRET_STR,
        algorithm=JWT_ALGORITHM,
        lifetime_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

# Authentication backend combination
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# =====================================================
# USER DATABASE DEPENDENCY - FIX ASYNC
# =====================================================

async def get_user_db(session: AsyncSession = Depends(get_db)):
    """
    Dependency per ottenere user database con SQLAlchemy.
    User model ora eredita da SQLAlchemyBaseUserTableUUID - fully compatible!
    """
    yield SQLAlchemyUserDatabase(session, User)

# =====================================================
# USER MANAGER SETUP - FIX TYPE ANNOTATIONS
# =====================================================

class UserManager(BaseUserManager[User, uuid.UUID]):
    """
    Custom User Manager per Ice Pulse con multi-tenancy.
    Gestisce business logic per registrazione, verifica, etc.
    """
    
    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET
    
    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Callback dopo registrazione utente."""
        print(f"✅ User registered: {user.email} in organization {user.organization_id}")
        
        # TODO: Invia email di benvenuto se email verification attiva
        # TODO: Log audit per compliance HACCP
    
    async def on_after_login(
        self, 
        user: User, 
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ):
        """Callback dopo login."""
        print(f"🔐 User logged in: {user.email}")
        
        # TODO: Log audit per compliance HACCP
        # TODO: Aggiorna last_login timestamp
    
    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Callback dopo richiesta verifica email."""
        print(f"📧 Verification requested for: {user.email}")
        
        # TODO: Invia email con token di verifica
    
    async def validate_password(self, password: str, user: User) -> None:
        """
        Validazione custom password per compliance HACCP.
        """
        if len(password) < 8:
            raise InvalidPasswordException(
                reason="Password must be at least 8 characters long"
            )
        
        if not any(c.isupper() for c in password):
            raise InvalidPasswordException(
                reason="Password must contain at least one uppercase letter"
            )
        
        if not any(c.islower() for c in password):
            raise InvalidPasswordException(
                reason="Password must contain at least one lowercase letter"  
            )
        
        if not any(c.isdigit() for c in password):
            raise InvalidPasswordException(
                reason="Password must contain at least one digit"
            )

# =====================================================
# USER MANAGER DEPENDENCY
# =====================================================

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Dependency per ottenere user manager."""
    yield UserManager(user_db)

# =====================================================
# FASTAPI-USERS MAIN INSTANCE
# =====================================================

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# =====================================================
# DEPENDENCIES EXPORTS
# =====================================================

# Current user dependencies per diversi livelli di accesso
current_active_user = fastapi_users.current_user(active=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

# =====================================================
# MULTI-TENANCY CUSTOM DEPENDENCIES  
# =====================================================

async def get_current_user_with_org_validation(
    current_user: User = Depends(current_active_user),
    organization_id: Optional[str] = None,
) -> User:
    """
    Dependency custom per validare accesso organization.
    
    Args:
        current_user: User dal JWT token
        organization_id: ID organizzazione da validare (da path/query param)
    
    Returns:
        User validato per organizzazione
        
    Raises:
        HTTPException: Se user non appartiene a organizzazione
    """
    
    # Se non è specificata org, usa quella dell'utente  
    if organization_id is None:
        return current_user
    
    # Validazione: user appartiene a questa organizzazione?
    if str(current_user.organization_id) != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: User does not belong to this organization"
        )
    
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(current_active_user),
) -> User:
    """
    Dependency per utenti con role admin o manager.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Admin or Manager role required"
        )
    
    return current_user

async def get_current_org_admin(
    current_user: User = Depends(current_active_user),
    organization_id: Optional[str] = None,
) -> User:
    """
    Dependency per admin di una specifica organizzazione.
    """
    
    # Validazione organization
    user_validated = await get_current_user_with_org_validation(
        current_user, organization_id
    )
    
    # Validazione role admin
    if user_validated.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied: Organization admin role required"
        )
    
    return user_validated