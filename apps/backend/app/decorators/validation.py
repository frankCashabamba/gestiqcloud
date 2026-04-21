"""
Common decorators for validation and error handling.
"""

import functools
from typing import Any, Callable

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID


def validate_uuid(value: str, field_name: str = "ID") -> UUID:
    """
    Validate and convert a string to UUID.
    
    Args:
        value: String value to validate
        field_name: Name of the field for error messages
        
    Returns:
        UUID object
        
    Raises:
        HTTPException: If value is not a valid UUID
    """
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid {field_name.lower()}: {value}"
        )


def extract_tenant_id(request: Request) -> str:
    """
    Extract tenant_id from request state.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Tenant ID string
        
    Raises:
        HTTPException: If tenant_id not found or invalid
    """
    claims = getattr(request.state, "access_claims", {})
    tenant = claims.get("tenant_id") or claims.get("tenant_id")
    
    if tenant is None:
        raise HTTPException(
            status_code=400, 
            detail="Tenant not found in token"
        )
    
    return str(tenant)


def validate_resource_exists(
    get_resource_func: Callable[[Session, str, str], Any],
    resource_name: str = "Resource"
):
    """
    Decorator to validate that a resource exists.
    
    Args:
        get_resource_func: Function that takes (db, tenant_id, resource_id) and returns resource
        resource_name: Name of the resource for error messages
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Find db and resource_id in kwargs
            db = None
            tenant_id = None
            resource_id = None
            
            for key, value in kwargs.items():
                if key == 'db':
                    db = value
                elif key == 'tenant_id':
                    tenant_id = value
                elif key in ['id', 'resource_id', f'{resource_name.lower()}_id']:
                    resource_id = value
            
            if not all([db, tenant_id, resource_id]):
                raise HTTPException(
                    status_code=500,
                    detail=f"Missing required parameters for {resource_name} validation"
                )
            
            # Validate resource exists
            resource = get_resource_func(db, tenant_id, str(resource_id))
            if not resource:
                raise HTTPException(
                    status_code=404,
                    detail=f"{resource_name} not found"
                )
            
            # Add resource to kwargs for the decorated function
            kwargs[f'validated_{resource_name.lower()}'] = resource
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def handle_not_found(resource_name: str = "Resource"):
    """
    Decorator to handle common "not found" errors from repositories.
    
    Args:
        resource_name: Name of the resource for error messages
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                if "not found" in str(e).lower():
                    raise HTTPException(
                        status_code=404,
                        detail=f"{resource_name} not found"
                    )
                raise
        return wrapper
    return decorator


def validate_pagination_params(func: Callable) -> Callable:
    """
    Decorator to validate and sanitize pagination parameters.
    
    Returns:
        Decorator function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Validate page
        if 'page' in kwargs:
            page = kwargs['page']
            if page is not None:
                try:
                    page = int(page)
                    kwargs['page'] = max(1, page)
                except (ValueError, TypeError):
                    kwargs['page'] = 1
        
        # Validate per_page
        if 'per_page' in kwargs:
            per_page = kwargs['per_page']
            if per_page is not None:
                try:
                    per_page = int(per_page)
                    kwargs['per_page'] = min(1000, max(1, per_page))  # Limit to 1000
                except (ValueError, TypeError):
                    kwargs['per_page'] = 20  # Default
        
        return func(*args, **kwargs)
    return wrapper


def tenant_required(func: Callable) -> Callable:
    """
    Decorator to ensure tenant_id is present in request.
    
    Returns:
        Decorator function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Find request in args or kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break
        
        if not request:
            raise HTTPException(
                status_code=500,
                detail="Request object not found for tenant validation"
            )
        
        # Extract and validate tenant_id
        tenant_id = extract_tenant_id(request)
        
        # Add tenant_id to kwargs if not present
        if 'tenant_id' not in kwargs:
            kwargs['tenant_id'] = tenant_id
        
        return func(*args, **kwargs)
    return wrapper
