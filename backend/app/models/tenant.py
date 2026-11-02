"""Modelo de Tenant (empresa contratante) para arquitectura SaaS Multitenant."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    """Empresa contratante independiente en la plataforma SaaS."""
    __tablename__ = "tenant"

    id = Column(Integer, primary_key=True)
    # Identificador alfanumérico único para URLs y login (ej: "luna", "moda-andina")
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    nombre = Column(String(150), nullable=False)
    nit = Column(String(30), nullable=True)
    telefono = Column(String(30), nullable=True)
    direccion = Column(String(250), nullable=True)
    pais = Column(String(50), default="Bolivia")
    moneda = Column(String(10), default="BOB")
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())

    # Relaciones
    suscripcion = relationship("Suscripcion", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    usuarios = relationship("Usuario", back_populates="tenant", cascade="all, delete-orphan")
