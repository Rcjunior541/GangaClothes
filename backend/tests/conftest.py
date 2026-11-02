import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import permisos as cat
from app.core.database import Base
from app.core.deps import get_db
from app.main import app
from app.models.seguridad import Permiso, RolPermiso
from app.models.usuarios import Rol

# Base de datos SQLite en memoria aislada para pruebas
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as s:
        for fila in cat.catalogo():
            p = s.query(Permiso).filter(Permiso.codigo == fila["codigo"]).first()
            if not p:
                s.add(Permiso(
                    codigo=fila["codigo"],
                    modulo=fila["modulo"],
                    accion=fila["accion"],
                    nombre=fila["nombre"],
                    descripcion=fila["descripcion"],
                ))
        s.flush()
        por_codigo = {p.codigo: p for p in s.query(Permiso).all()}
        for nombre_rol, codigos in cat.PERMISOS_POR_ROL.items():
            r = s.query(Rol).filter(Rol.nombre == nombre_rol).first()
            if not r:
                r = Rol(nombre=nombre_rol, descripcion=cat.DESCRIPCION_ROLES.get(nombre_rol))
                s.add(r)
                s.flush()
            if nombre_rol == "administrador":
                codigos = cat.todos_los_codigos()
            actuales = {rp.permiso_id for rp in s.query(RolPermiso).filter(RolPermiso.rol_id == r.id).all()}
            for c in codigos:
                perm = por_codigo.get(c)
                if perm and perm.id not in actuales:
                    s.add(RolPermiso(rol_id=r.id, permiso_id=perm.id))
        s.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            db.info.pop("tenant_scope", None)
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
