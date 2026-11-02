from sqlalchemy import Column, ForeignKey, Integer, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria

from app.core.config import settings

if settings.database_url.startswith("sqlite"):
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
else:
    # Neon suspende la base cuando no hay trafico y corta las conexiones abiertas.
    # pool_pre_ping descarta la conexion muerta antes de usarla (si no, la primera
    # peticion despues de la pausa responde 500) y pool_recycle la renueva antes.
    engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=280)

if settings.database_url.startswith("sqlite"):
    # SQLite ignora las claves foraneas salvo que se pidan en cada conexion.
    # Sin esto, en local se borrarian filas que PostgreSQL (Neon) rechazaria,
    # y nunca se ejecutaria el "desactivar en lugar de eliminar" de comunes.py.
    @event.listens_for(engine, "connect")
    def _activar_claves_foraneas(conexion, _registro):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Mixin para modelos de datos que pertenecen lógicamente a un Tenant."""

    tenant_id = Column(
        Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=True, index=True
    )


@event.listens_for(Session, "do_orm_execute")
def _aislamiento_multitenant(execute_state):
    """Garantiza aislamiento lógico por tenant en el motor del ORM.

    Si session.info['tenant_scope'] está definido, inyecta automáticamente
    la cláusula 'WHERE tenant_id = :scope' en todas las consultas SELECT, UPDATE y DELETE
    sobre modelos que hereden de TenantMixin.
    """
    if (
        not execute_state.is_select
        and not execute_state.is_update
        and not execute_state.is_delete
    ):
        return
    session = execute_state.session
    tenant_scope = session.info.get("tenant_scope")
    if tenant_scope is not None:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                TenantMixin,
                lambda cls: cls.tenant_id == tenant_scope,
                include_aliases=True,
            )
        )


def to_dict(obj):
    """Convierte una fila SQLAlchemy en dict serializable."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
