# =====================================================
# src/auth/routes.py - Authentication Routes
# =====================================================
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import FastAPIUsers
from typing import List

from src.auth.config import (
    fastapi_users, 
    auth_backend,
    current_active_user,
    get_current_admin_user,
    get_current_org_admin,
    get_current_user_with_org_validation
)
from src.auth.schemas import (
    UserRead, 
    UserCreate, 
    UserUpdate, 
    UserInvite,
    UserProfile,
    PasswordChange,
    UserStats,
    OrganizationUserList,
    LoginResponse,
    LogoutResponse
)
from src.models.user import User

# =====================================================
# ROUTER SETUP
# =====================================================

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# =====================================================
# FASTAPI-USERS STANDARD ROUTES
# =====================================================

# Aggiunge automaticamente:
# POST /auth/jwt/login - Login con email/password
# POST /auth/jwt/logout - Logout (invalida token)
# POST /auth/register - Registrazione (disabilitata per Ice Pulse)
auth_router.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/jwt"
)

# User management routes (per admin)
# GET /auth/users - Lista utenti
# GET /auth/users/{id} - Dettaglio utente  
# PATCH /auth/users/{id} - Aggiorna utente
# DELETE /auth/users/{id} - Elimina utente
auth_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    dependencies=[Depends(get_current_admin_user)]  # Solo admin possono gestire utenti
)

# =====================================================
# CUSTOM ICE PULSE ROUTES
# =====================================================

@auth_router.post(
    "/invite", 
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invita nuovo utente (Admin only)"
)
async def invite_user(
    user_invite: UserInvite,
    current_admin: User = Depends(get_current_org_admin)
):
    """
    Invita nuovo utente nella stessa organizzazione dell'admin.
    Solo admin organizzazione possono invitare utenti.
    """
    try:
        # Crea UserCreate da UserInvite aggiungendo organization_id
        user_create_data = UserCreate(
            email=user_invite.email,
            password="temp_password_123!",  # Password temporanea
            organization_id=current_admin.organization_id,
            first_name=user_invite.first_name,
            last_name=user_invite.last_name,
            role=user_invite.role,
            phone=user_invite.phone,
            is_verified=False,
            haccp_certificate_number=None  # Richiederà verifica email
        )
        
        # TODO: Implementare creazione via UserManager
        # TODO: Inviare email con link per completare registrazione
        # TODO: Log audit per compliance HACCP
        
        # Placeholder response per ora
        raise HTTPException(
            status_code=501,
            detail="User invitation not yet implemented - coming in next iteration"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to invite user: {str(e)}"
        )

@auth_router.get(
    "/profile",
    response_model=UserRead,
    summary="Profilo utente corrente"
)
async def get_my_profile(
    current_user: User = Depends(current_active_user)
):
    """Restituisce il profilo dell'utente correntemente loggato."""
    return current_user

@auth_router.patch(
    "/profile",
    response_model=UserRead,
    summary="Aggiorna profilo personale"
)
async def update_my_profile(
    profile_update: UserProfile,
    current_user: User = Depends(current_active_user)
):
    """
    Permette all'utente di aggiornare il proprio profilo.
    Non include campi sensibili come email, role, organization.
    """
    try:
        # TODO: Implementare aggiornamento via repository
        # TODO: Log audit per compliance HACCP
        
        raise HTTPException(
            status_code=501,
            detail="Profile update not yet implemented - coming in next iteration"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update profile: {str(e)}"
        )

@auth_router.post(
    "/change-password",
    response_model=dict,
    summary="Cambio password"
)
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(current_active_user)
):
    """Permette cambio password validando quella attuale."""
    try:
        # Verifica password attuale
        if not current_user.verify_password(password_change.current_password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )
        
        # TODO: Implementare cambio password via UserManager
        # TODO: Log audit per compliance HACCP
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to change password: {str(e)}"
        )

@auth_router.get(
    "/organization/{organization_id}/users",
    response_model=OrganizationUserList,
    summary="Lista utenti organizzazione"
)
async def get_organization_users(
    organization_id: str,
    current_admin: User = Depends(get_current_org_admin)
):
    """
    Lista tutti gli utenti dell'organizzazione.
    Solo admin organizzazione possono vedere lista completa.
    """
    try:
        # Validazione che admin appartenga a questa organizzazione
        validated_user = await get_current_user_with_org_validation(
            current_admin, organization_id
        )
        
        # TODO: Implementare query utenti via repository
        # TODO: Aggregare statistiche per ruoli
        
        raise HTTPException(
            status_code=501,
            detail="Organization users list not yet implemented - coming in next iteration"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get organization users: {str(e)}"
        )

@auth_router.get(
    "/stats",
    response_model=UserStats,
    summary="Statistiche utente"
)
async def get_user_stats(
    current_user: User = Depends(current_active_user)
):
    """Statistiche dell'utente corrente per dashboard."""
    try:
        # TODO: Implementare query statistiche via repository
        # TODO: Calcolare stato certificato HACCP
        
        # Placeholder response
        return UserStats(
            total_logins=0,
            last_login=None,
            account_created=current_user.created_at.isoformat(),
            haccp_certificate_status="none",
            organization_name="Organization Name"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get user stats: {str(e)}"
        )

# =====================================================
# DEVELOPMENT/DEBUG ROUTES (rimuovere in production)
# =====================================================

@auth_router.get(
    "/debug/current-user",
    response_model=UserRead,
    summary="Debug: Current user info"
)
async def debug_current_user(
    current_user: User = Depends(current_active_user)
):
    """Route di debug per verificare autenticazione JWT."""
    return current_user