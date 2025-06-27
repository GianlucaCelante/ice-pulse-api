# src/repositories/user_repository.py
"""
UserRepository - Repository pattern per gestione utenti.

RESPONSABILITÀ:
- CRUD operations per User
- Queries specifiche per autenticazione
- Gestione password hashing tramite User methods
- Multi-tenancy (filtro per organization_id)
- Queries per HACCP compliance
- Login tracking e security
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.models.user import User
from src.database.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    DatabaseError
)


class UserRepository:
    """Repository per operazioni CRUD su User model"""
    
    def __init__(self, db_session: Session):
        """
        Inizializza il repository con una sessione database.
        
        Args:
            db_session: SQLAlchemy session per database operations
        """
        self.db = db_session
    
    # ==========================================
    # CRUD OPERATIONS
    # ==========================================
    
    def create(self, user_data: Dict[str, Any]) -> User:
        """
        Crea un nuovo utente.
        
        Args:
            user_data: Dictionary con i dati dell'utente
                      Include 'password' in plain text che verrà hashata
            
        Returns:
            User: L'utente creato
            
        Raises:
            DuplicateEntityError: Se email già esistente
            DatabaseError: Per altri errori database
        """
        try:
            # Estrai password prima di creare User
            user_data_copy = user_data.copy()  # ←← NON modificare l'originale
            password = user_data_copy.pop('password', None)
            user = User(**user_data_copy)
            
            # Hash password usando il metodo del model
            if password:
                user.set_password(password)
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig)
            
            if 'users_email_key' in error_msg or 'email' in error_msg:
                raise DuplicateEntityError(f"User with email '{user_data.get('email')}' already exists")
            else:
                raise DatabaseError(f"Failed to create user: {error_msg}")
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create user: {str(e)}")
    
    def get_by_id(self, user_id: UUID, organization_id: Optional[UUID] = None) -> Optional[User]:
        """
        Recupera utente per ID.
        
        Args:
            user_id: UUID dell'utente
            organization_id: UUID organizzazione per multi-tenancy
            
        Returns:
            Optional[User]: L'utente se trovato, None altrimenti
        """
        query = select(User).where(User.id == user_id)
        
        # Multi-tenancy filter
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    def get_by_email(self, email: str, organization_id: Optional[UUID] = None) -> Optional[User]:
        """
        Recupera utente per email.
        
        Args:
            email: Email dell'utente
            organization_id: UUID organizzazione per multi-tenancy
            
        Returns:
            Optional[User]: L'utente se trovato, None altrimenti
        """
        query = select(User).where(User.email == email)
        
        # Multi-tenancy filter
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    def update(self, user_id: UUID, user_data: Dict[str, Any], organization_id: Optional[UUID] = None) -> User:
        """
        Aggiorna un utente esistente.
        
        Args:
            user_id: UUID dell'utente da aggiornare
            user_data: Dictionary con i nuovi dati
            organization_id: UUID organizzazione per multi-tenancy
            
        Returns:
            User: L'utente aggiornato
            
        Raises:
            EntityNotFoundError: Se utente non trovato
            DuplicateEntityError: Se email già in uso
            DatabaseError: Per altri errori database
        """
        try:
            user = self.get_by_id(user_id, organization_id)
            if not user:
                raise EntityNotFoundError(f"User with id {user_id} not found")
            
            # Gestisci password separatamente
            password = user_data.pop('password', None)
            if password:
                user.set_password(password)
            
            # Aggiorna i campi
            for key, value in user_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig)
            
            if 'users_email_key' in error_msg or 'email' in error_msg:
                raise DuplicateEntityError(f"Email '{user_data.get('email')}' already in use")
            else:
                raise DatabaseError(f"Failed to update user: {error_msg}")
        except EntityNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to update user: {str(e)}")
    
    def delete(self, user_id: UUID, organization_id: Optional[UUID] = None) -> bool:
        """
        Elimina un utente.
        
        Args:
            user_id: UUID dell'utente da eliminare
            organization_id: UUID organizzazione per multi-tenancy
            
        Returns:
            bool: True se eliminato, False se non trovato
            
        Raises:
            DatabaseError: Per errori database
        """
        try:
            user = self.get_by_id(user_id, organization_id)
            if not user:
                return False
            
            self.db.delete(user)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to delete user: {str(e)}")
    
    # ==========================================
    # QUERY METHODS
    # ==========================================
    
    def get_all(
        self, 
        organization_id: Optional[UUID] = None,
        active_only: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[User]:
        """
        Recupera lista utenti con filtri opzionali.
        
        Args:
            organization_id: Filtra per organizzazione
            active_only: Solo utenti attivi
            limit: Limite numero risultati
            offset: Offset per paginazione
            
        Returns:
            List[User]: Lista utenti
        """
        query = select(User)
        
        # Filtri
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        if active_only:
            query = query.where(User.is_active == True)
        
        # Ordinamento
        query = query.order_by(desc(User.created_at))
        
        # Paginazione
        if offset > 0:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def search_users(
        self,
        search_term: str,
        organization_id: Optional[UUID] = None,
        role_filter: Optional[str] = None,
        active_only: bool = True
    ) -> List[User]:
        """
        Ricerca utenti per email, nome o cognome.
        
        Args:
            search_term: Termine di ricerca
            organization_id: Filtra per organizzazione
            role_filter: Filtra per ruolo specifico
            active_only: Solo utenti attivi
            
        Returns:
            List[User]: Lista utenti che matchano la ricerca
        """
        # Costruisci la query base
        query = select(User)
        
        # Filtro ricerca (case-insensitive)
        search_pattern = f"%{search_term.lower()}%"
        search_condition = or_(
            func.lower(User.email).contains(search_pattern),
            func.lower(User.first_name).contains(search_pattern),
            func.lower(User.last_name).contains(search_pattern)
        )
        query = query.where(search_condition)
        
        # Filtri aggiuntivi
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        if role_filter:
            query = query.where(User.role == role_filter)
        
        if active_only:
            query = query.where(User.is_active == True)
        
        # Ordinamento per rilevanza (email exact match prima)
        query = query.order_by(
            func.lower(User.email) == search_term.lower(),
            User.email
        )
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_by_role(
        self, 
        role: str,
        organization_id: Optional[UUID] = None,
        active_only: bool = True
    ) -> List[User]:
        """
        Recupera utenti per ruolo.
        
        Args:
            role: Ruolo da filtrare ('admin', 'manager', 'operator', 'viewer')
            organization_id: Filtra per organizzazione
            active_only: Solo utenti attivi
            
        Returns:
            List[User]: Lista utenti con il ruolo specificato
        """
        query = select(User).where(User.role == role)
        
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        if active_only:
            query = query.where(User.is_active == True)
        
        query = query.order_by(User.email)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    # ==========================================
    # AUTHENTICATION METHODS
    # ==========================================
    
    def authenticate_user(self, email: str, password: str, organization_id: Optional[UUID] = None) -> Optional[User]:
        """
        Autentica un utente tramite email/password.
        
        Args:
            email: Email dell'utente
            password: Password in plain text
            organization_id: UUID organizzazione
            
        Returns:
            Optional[User]: Utente se credenziali valide, None altrimenti
        """
        user = self.get_by_email(email, organization_id)
        
        if not user or not user.is_active:
            return None
        
        # Verifica se account è bloccato
        if user.is_account_locked():
            return None
        
        # Verifica password usando il metodo del model
        if user.verify_password(password):
            # Reset failed attempts e update last login
            user.reset_failed_attempts()
            user.update_last_login()
            self.db.commit()
            return user
        else:
            # Incrementa failed attempts
            user.increment_failed_attempts()
            self.db.commit()
            return None
    
    def unlock_user_account(self, user_id: UUID, organization_id: Optional[UUID] = None) -> bool:
        """
        Sblocca account utente resettando failed attempts.
        
        Args:
            user_id: UUID dell'utente
            organization_id: UUID organizzazione
            
        Returns:
            bool: True se sbloccato, False se utente non trovato
        """
        user = self.get_by_id(user_id, organization_id)
        if not user:
            return False
        
        user.reset_failed_attempts()
        self.db.commit()
        return True
    
    # ==========================================
    # HACCP COMPLIANCE METHODS
    # ==========================================
    
    def get_haccp_certified_users(self, organization_id: Optional[UUID] = None) -> List[User]:
        """
        Recupera utenti con certificazione HACCP valida.
        
        Args:
            organization_id: Filtra per organizzazione
            
        Returns:
            List[User]: Lista utenti certificati HACCP
        """
        query = select(User).where(
            and_(
                User.haccp_certificate_number.isnot(None),
                User.haccp_certificate_expiry.isnot(None),
                User.haccp_certificate_expiry > func.current_date(),
                User.is_active == True
            )
        )
        
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        query = query.order_by(User.haccp_certificate_expiry)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_expiring_certificates(
        self, 
        days_ahead: int = 30,
        organization_id: Optional[UUID] = None
    ) -> List[User]:
        """
        Recupera utenti con certificazione HACCP in scadenza.
        
        Args:
            days_ahead: Giorni di anticipo per alert scadenza
            organization_id: Filtra per organizzazione
            
        Returns:
            List[User]: Lista utenti con certificazione in scadenza
        """
        from sqlalchemy import Date
        expiry_threshold = func.current_date() + func.cast(func.make_interval(days=days_ahead), Date)
        
        query = select(User).where(
            and_(
                User.haccp_certificate_expiry.isnot(None),
                User.haccp_certificate_expiry <= expiry_threshold,
                User.haccp_certificate_expiry > func.current_date(),
                User.is_active == True
            )
        )
        
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        query = query.order_by(User.haccp_certificate_expiry)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    # ==========================================
    # STATISTICS METHODS
    # ==========================================
    
    def count_users_by_role(self, organization_id: Optional[UUID] = None) -> Dict[str, int]:
        """
        Conta utenti per ruolo.
        
        Args:
            organization_id: Filtra per organizzazione
            
        Returns:
            Dict[str, int]: Dizionario ruolo -> count
        """
        query = select(User.role, func.count(User.id)).group_by(User.role)
        
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        result = self.db.execute(query)
        return {row[0]: row[1] for row in result.fetchall()}
    
    def get_user_stats(self, organization_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Recupera statistiche utenti per organizzazione.
        
        Args:
            organization_id: Filtra per organizzazione
            
        Returns:
            Dict[str, Any]: Statistiche complete
        """
        base_query = select(User)
        if organization_id:
            base_query = base_query.where(User.organization_id == organization_id)
        
        # Count totale utenti
        total_query = select(func.count(User.id))
        if organization_id:
            total_query = total_query.where(User.organization_id == organization_id)
        total_users = self.db.execute(total_query).scalar()
        
        # Count utenti attivi
        active_query = select(func.count(User.id)).where(User.is_active == True)
        if organization_id:
            active_query = active_query.where(User.organization_id == organization_id)
        active_users = self.db.execute(active_query).scalar()
        
        # Count utenti verificati
        verified_query = select(func.count(User.id)).where(User.is_verified == True)
        if organization_id:
            verified_query = verified_query.where(User.organization_id == organization_id)
        verified_users = self.db.execute(verified_query).scalar()
        
        # Count certificati HACCP
        haccp_query = select(func.count(User.id)).where(
            and_(
                User.haccp_certificate_number.isnot(None),
                User.haccp_certificate_expiry > func.current_date()
            )
        )
        if organization_id:
            haccp_query = haccp_query.where(User.organization_id == organization_id)
        haccp_certified = self.db.execute(haccp_query).scalar()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "haccp_certified": haccp_certified,
            "inactive_users": (total_users or 0) - (active_users or 0),
            "users_by_role": self.count_users_by_role(organization_id)
        }