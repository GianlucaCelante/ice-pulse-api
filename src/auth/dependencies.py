# =====================================================
# src/auth/dependencies.py - Authentication Dependencies
# =====================================================
from typing import Optional
from fastapi import Depends, HTTPException, Path, Query
from fastapi_users import FastAPIUsers

from src.auth.config import (
    fastapi_users,
    current_active_user,
    current_verified_user,
    current_superuser
)
from src.models.user import User

# =====================================================
# BASIC AUTH DEPENDENCIES (da config.py)
# =====================================================

# Re-export per convenienza
get_current_user = current_active_user
get_current_verified_user = current_verified_user  
get_current_superuser = current_superuser

# =====================================================
# ROLE-BASED DEPENDENCIES
# =====================================================

async def get_current_admin_user(
    current_user: User = Depends(current_active_user),
) -> User:
    """
    Dependency per utenti con role admin o manager.
    Usare per operazioni di gestione organizzazione.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Admin or Manager role required"
        )
    
    return current_user

async def get_current_operator_user(
    current_user: User = Depends(current_active_user),
) -> User:
    """
    Dependency per utenti con role operator o superiore.
    Usare per operazioni sui dati/sensori.
    """
    allowed_roles = ["admin", "manager", "operator"]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Operator role or higher required"
        )
    
    return current_user

async def get_current_viewer_user(
    current_user: User = Depends(current_active_user),
) -> User:
    """
    Dependency per qualsiasi utente attivo.
    Usare per operazioni di sola lettura.
    """
    # Tutti gli utenti attivi possono visualizzare
    return current_user

# =====================================================
# ORGANIZATION-BASED DEPENDENCIES
# =====================================================

async def get_current_user_with_org_validation(
    current_user: User = Depends(current_active_user),
    organization_id: Optional[str] = None,
) -> User:
    """
    Dependency per validare accesso organization.
    
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

async def get_current_org_admin(
    current_user: User = Depends(current_active_user),
    organization_id: Optional[str] = None,
) -> User:
    """
    Dependency per admin di una specifica organizzazione.
    Usare per operazioni di gestione utenti/settings dell'org.
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

async def get_current_org_manager(
    current_user: User = Depends(current_active_user),
    organization_id: Optional[str] = None,
) -> User:
    """
    Dependency per manager di una specifica organizzazione.
    Usare per operazioni di gestione operativa.
    """
    
    # Validazione organization
    user_validated = await get_current_user_with_org_validation(
        current_user, organization_id
    )
    
    # Validazione role manager o superiore
    if user_validated.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Manager role or higher required"
        )
    
    return user_validated

# =====================================================
# PATH PARAMETER DEPENDENCIES
# =====================================================

async def validate_organization_path(
    organization_id: str = Path(..., description="Organization ID"),
    current_user: User = Depends(current_active_user),
) -> tuple[str, User]:
    """
    Dependency per path parameter organization_id.
    Valida che user appartenga all'organizzazione.
    
    Returns:
        Tuple (organization_id, validated_user)
    """
    
    validated_user = await get_current_user_with_org_validation(
        current_user, organization_id
    )
    
    return organization_id, validated_user

async def validate_user_path(
    user_id: str = Path(..., description="User ID"),
    organization_id: str = Path(..., description="Organization ID"),
    current_admin: User = Depends(get_current_org_admin),
) -> tuple[str, str, User]:
    """
    Dependency per path parameter user_id in contesto organization.
    Solo admin org possono gestire altri utenti.
    
    Returns:
        Tuple (user_id, organization_id, admin_user)
    """
    
    # Admin validation già fatta in get_current_org_admin
    return user_id, organization_id, current_admin

# =====================================================
# QUERY PARAMETER DEPENDENCIES
# =====================================================

async def pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """
    Dependency per parametri paginazione.
    
    Returns:
        Dict con offset e limit per query database
    """
    
    offset = (page - 1) * limit
    
    return {
        "offset": offset,
        "limit": limit,
        "page": page
    }

async def filter_params(
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name/email"),
) -> dict:
    """
    Dependency per parametri filtro liste utenti.
    
    Returns:
        Dict con filtri per query database
    """
    
    filters = {}
    
    if role is not None:
        allowed_roles = ['admin', 'manager', 'operator', 'viewer']
        if role not in allowed_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
            )
        filters["role"] = role
    
    if is_active is not None:
        filters["is_active"] = is_active
    
    if search is not None:
        filters["search"] = search.strip()
    
    return filters

# =====================================================
# COMBINED DEPENDENCIES
# =====================================================

async def get_organization_context(
    organization_id: str = Path(...),
    current_user: User = Depends(current_active_user),
    pagination: dict = Depends(pagination_params),
    filters: dict = Depends(filter_params),
) -> dict:
    """
    Dependency combinata per context organizzazione completo.
    Include validazione user, paginazione e filtri.
    
    Returns:
        Dict con tutto il context necessario per query org
    """
    
    # Validazione organization
    validated_user = await get_current_user_with_org_validation(
        current_user, organization_id
    )
    
    return {
        "organization_id": organization_id,
        "current_user": validated_user,
        "pagination": pagination,
        "filters": filters
    }