"""Modelos de Plan y Suscripción para regular el acceso por tenant (Desafío VI)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Plan(Base):
    """Catálogo de planes de suscripción configurables por el Superadmin."""
    __tablename__ = "plan"

    id = Column(Integer, primary_key=True)
    # "basico" | "profesional"
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    nombre = Column(String(100), nullable=False)
    precio_mensual = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    # Límites definidos por el enunciado: Básico=2, Profesional=10
    limite_sucursales = Column(Integer, default=2, nullable=False)
    # Habilitación de IA generativa (Texto/Voz): Básico=False, Profesional=True
    permite_ia_generativa = Column(Boolean, default=False, nullable=False)
    descripcion = Column(String(250), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)

    suscripciones = relationship("Suscripcion", back_populates="plan")


class Suscripcion(Base):
    """Vínculo 1 a 1 entre una empresa contratante (Tenant) y su Plan activo."""
    __tablename__ = "suscripcion"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan_id = Column(Integer, ForeignKey("plan.id"), nullable=False)
    # "activa" | "vencida" | "cancelada"
    estado = Column(String(20), default="activa", nullable=False)
    fecha_inicio = Column(DateTime, server_default=func.now(), nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=True)
    # "mensual" | "anual"
    ciclo_facturacion = Column(String(20), default="mensual", nullable=False)

    tenant = relationship("Tenant", back_populates="suscripcion")
    plan = relationship("Plan", back_populates="suscripciones")
