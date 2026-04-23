# Rutas de API para gestion de usuarios.

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.user_controller import register_user_controller
from app.database import get_db
from app.models.user_schemas import UserRegistrationRequest, UserRegistrationResponse
from app.dependencies.auth import require_web_superuser
from app.repositories.user_repository import UserRepository
from app.models.user import Usuario

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


@router.post(
    "/registro",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user_endpoint(
    payload: UserRegistrationRequest,
    db: Session = Depends(get_db),
) -> UserRegistrationResponse:
    # Endpoint CU1: recibe datos del usuario y devuelve confirmacion de registro.
    return register_user_controller(payload, db)


@router.get(
    "/",
    response_model=list,
    status_code=status.HTTP_200_OK,
)
def list_users_endpoint(
    current_user=Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """Lista usuarios registrados con sus roles. Acceso solo para superusuarios (canal web)."""
    repository = UserRepository(db)
    rows = db.query(Usuario).order_by(Usuario.creado_en.desc()).all()
    result: list[dict] = []
    for u in rows:
        roles = list(repository.get_role_names_by_user_id(u.id))
        result.append({
            "id": u.id,
            "nombre": u.nombre,
            "correo": u.correo,
            "roles": roles,
            "creado_en": u.creado_en.isoformat() if u.creado_en else None,
        })
    return result


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
def delete_user_endpoint(
    user_id: int,
    current_user=Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """Elimina un usuario del sistema. Acceso solo para superusuarios (canal web)."""
    from fastapi import HTTPException
    
    repository = UserRepository(db)
    
    # Verificar que el usuario existe
    user = repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    
    # Evitar que el superadmin se elimine a sí mismo
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta."
        )
    
    try:
        repository.delete_user(user_id)
        db.commit()
        return {"message": f"Usuario {user.nombre} eliminado correctamente.", "user_id": user_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar usuario: {str(e)}"
        )
