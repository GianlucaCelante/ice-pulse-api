# src/database/exceptions.py
"""
Custom exceptions per database operations.

Queste eccezioni forniscono error handling più specifico
e messagi di errore più informativi rispetto alle eccezioni standard.
"""


class DatabaseError(Exception):
    """
    Base exception per errori database generici.
    
    Usata per errori di connessione, transazioni fallite,
    constraint violations non specifiche, etc.
    """
    pass


class EntityNotFoundError(DatabaseError):
    """
    Exception per entity non trovate.
    
    Sollevata quando si cerca di recuperare/aggiornare/eliminare
    un'entity che non esiste nel database.
    
    Examples:
        - get_by_id() con ID non esistente
        - update() su record cancellato
        - delete() su record già eliminato
    """
    pass


class DuplicateEntityError(DatabaseError):
    """
    Exception per violazioni di unique constraints.
    
    Sollevata quando si tenta di creare/aggiornare un'entity
    con valori che violano constraint di unicità.
    
    Examples:
        - Email già esistente
        - Slug già in uso
        - Chiavi duplicate
    """
    pass


class ValidationError(DatabaseError):
    """
    Exception per errori di validazione dati.
    
    Sollevata quando i dati non rispettano i constraint
    di business logic o validation rules.
    
    Examples:
        - Check constraints violati
        - Foreign key non valide
        - Formati dati incorretti
    """
    pass


class PermissionError(DatabaseError):
    """
    Exception per errori di autorizzazione.
    
    Sollevata quando un'operazione non è permessa
    per motivi di sicurezza o multi-tenancy.
    
    Examples:
        - Accesso cross-organization negato
        - Operazione non autorizzata per il ruolo
        - RLS policy violations
    """
    pass


class ConcurrencyError(DatabaseError):
    """
    Exception per conflitti di concorrenza.
    
    Sollevata quando operazioni simultanee causano
    conflitti di versioning o lock.
    
    Examples:
        - Optimistic locking failures
        - Deadlock detection
        - Transaction conflicts
    """
    pass


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def handle_integrity_error(error, entity_name: str = "Entity"):
    """
    Converte IntegrityError SQLAlchemy in exception custom più specifiche.
    
    Args:
        error: SQLAlchemy IntegrityError
        entity_name: Nome dell'entity per messaggi di errore più chiari
        
    Raises:
        DuplicateEntityError: Per unique constraint violations
        ValidationError: Per check constraint violations
        DatabaseError: Per altri integrity errors
    """
    error_msg = str(error.orig).lower()
    
    # Unique constraint violations
    if any(keyword in error_msg for keyword in ['unique', 'duplicate', 'already exists']):
        if 'email' in error_msg:
            raise DuplicateEntityError(f"{entity_name} with this email already exists")
        elif 'slug' in error_msg:
            raise DuplicateEntityError(f"{entity_name} with this slug already exists")
        else:
            raise DuplicateEntityError(f"Duplicate {entity_name.lower()} found")
    
    # Check constraint violations
    elif any(keyword in error_msg for keyword in ['check', 'constraint', 'violates']):
        raise ValidationError(f"Data validation failed for {entity_name.lower()}: {error_msg}")
    
    # Foreign key violations
    elif any(keyword in error_msg for keyword in ['foreign key', 'referenced', 'does not exist']):
        raise ValidationError(f"Referenced {entity_name.lower()} does not exist")
    
    # Generic integrity error
    else:
        raise DatabaseError(f"Database integrity error for {entity_name.lower()}: {error_msg}")


def handle_sqlalchemy_error(error, operation: str = "operation", entity_name: str = "entity"):
    """
    Converte errori SQLAlchemy generici in exception custom.
    
    Args:
        error: SQLAlchemy exception
        operation: Nome dell'operazione (create, update, delete, etc.)
        entity_name: Nome dell'entity
        
    Raises:
        DatabaseError: Con messaggio appropriato
    """
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError
    
    if isinstance(error, IntegrityError):
        handle_integrity_error(error, entity_name)
    elif isinstance(error, SQLAlchemyError):
        raise DatabaseError(f"Database error during {operation} {entity_name.lower()}: {str(error)}")
    else:
        raise DatabaseError(f"Unexpected error during {operation} {entity_name.lower()}: {str(error)}")


# ==========================================
# DECORATORS
# ==========================================

def handle_database_errors(entity_name: str = "Entity"):
    """
    Decorator per automatic error handling nei repository methods.
    
    Usage:
        @handle_database_errors("User")
        def create_user(self, data):
            # method implementation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (EntityNotFoundError, DuplicateEntityError, ValidationError, PermissionError):
                # Re-raise custom exceptions as-is
                raise
            except Exception as e:
                # Convert other exceptions to DatabaseError
                operation = func.__name__.replace('_', ' ')
                handle_sqlalchemy_error(e, operation, entity_name)
        
        return wrapper
    return decorator