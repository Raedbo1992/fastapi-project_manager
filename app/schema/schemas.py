from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import date, datetime
from typing import Optional, Dict, List
from typing import Union 
from datetime import date


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    username: str

class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    username: str
    password: str

class Usuario(UsuarioBase):
    id: int
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CategoriaBase(BaseModel):
    nombre: str
    tipo: str

class CategoriaCreate(CategoriaBase):
    pass

class Categoria(CategoriaBase):
    id: int
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)

class GastoBase(BaseModel):
    categoria_id: int
    valor: float
    fecha_limite: Optional[date] = None
    pagado: bool = False
    notas: Optional[str] = None

class GastoCreate(GastoBase):
    pass

class GastoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    valor: Optional[float] = None
    fecha_limite: Optional[date] = None
    pagado: Optional[bool] = None
    notas: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class Gasto(GastoBase):
    id: int
    usuario_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ✅ CORREGIDO - IngresoBase con estado
class IngresoBase(BaseModel):
    valor: float
    fecha: date
    estado: str = 'pendiente'  # ✅ AGREGADO
    notas: Optional[str] = None

class IngresoCreate(IngresoBase):
    pass

# ✅ CORREGIR IngresoCreate
class IngresoCreate(BaseModel):
    categoria_id: int
    valor: float
    fecha: date
    estado: str = 'pendiente'
    notas: Optional[str] = None


    model_config = ConfigDict(from_attributes=True)


# ✅ CORREGIR IngresoUpdate
class IngresoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    valor: Optional[float] = None
    fecha: Optional[date] = None
    estado: Optional[str] = None
    notas: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    
class Ingreso(IngresoBase):
    id: int
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class PendienteBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    estado: str = 'pendiente'
    prioridad: str = 'media'
    fecha_limite: Optional[datetime] = None
    recordatorio: Optional[datetime] = None

class PendienteCreate(PendienteBase):
    pass

class PendienteUpdate(PendienteBase):
    pass

class Pendiente(PendienteBase):
    id: int
    usuario_id: int
    fecha_creacion: datetime
    
    class Config:
        orm_mode = True

class DashboardStats(BaseModel):
    salario_actual: float
    total_gastos: float
    total_ingresos: float
    saldo_disponible: float
    gastos_por_categoria: Dict[str, float]
    gastos_por_tipo: Dict[str, float]
    variacion_ingresos: float = 0.0
    variacion_gastos: float = 0.0
    porcentaje_ahorro: float = 0.0
    categoria_mayor: Dict[str, Union[str, float]] = {
        'nombre': 'Ninguna',
        'valor': 0.0,
        'porcentaje': 0.0
    }
    evolucion_mensual: Dict[str, List] = {
        'labels': [],
        'ingresos': [],
        'gastos': []
    }
    promedio_mensual: float = 0.0
    porcentaje_fijos: float = 0.0
    porcentaje_variables: float = 0.0

    model_config = ConfigDict(from_attributes=True)

class ContrasenaBase(BaseModel):
    servicio: str
    usuario: str
    contrasena: str
    url: Optional[str] = None
    notas: Optional[str] = None

class ContrasenaCreate(ContrasenaBase):
    pass

class ContrasenaUpdate(BaseModel):
    servicio: Optional[str] = None
    usuario: Optional[str] = None
    contrasena: Optional[str] = None
    url: Optional[str] = None
    notas: Optional[str] = None

class Contrasena(ContrasenaBase):
    id: int
    usuario_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CumpleanoBase(BaseModel):
    nombre_persona: str
    fecha_nacimiento: date
    telefono: Optional[str] = None
    email: Optional[str] = None
    relacion: Optional[str] = None
    notas: Optional[str] = None
    notificar_dias_antes: int = 7

class CumpleanoCreate(CumpleanoBase):
    pass

class CumpleanoUpdate(BaseModel):
    nombre_persona: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    relacion: Optional[str] = None
    notas: Optional[str] = None
    notificar_dias_antes: Optional[int] = None

class Cumpleano(CumpleanoBase):
    id: int
    usuario_id: int
    created_at: datetime
    updated_at: datetime
    dias_hasta_cumpleanos: Optional[int] = None
    edad: Optional[int] = None
    
    class Config:
        from_attributes = True



# ----------------------------------------
# 📌 Schemas para Crédito
# ----------------------------------------
# En schemas.py
class CreditoBase(BaseModel):
    nombre_credito: str
    monto: float
    interes: float
    plazo_meses: int
    frecuencia_pago: str = "mensual"
    fecha_inicio: date
    seguro: float = 0.0
    cuota_manual: float = 0.0  # ✅ Campo para modo manual
    observaciones: Optional[str] = None

class CreditoCreate(CreditoBase):
    pass

class CreditoUpdate(BaseModel):
    nombre_credito: Optional[str] = None
    monto: Optional[float] = None
    interes: Optional[float] = None
    plazo_meses: Optional[int] = None
    frecuencia_pago: Optional[str] = None
    fecha_inicio: Optional[date] = None
    seguro: Optional[float] = None
    cuota_manual: Optional[float] = None  # ✅ Se puede actualizar
    observaciones: Optional[str] = None



# ============================================================================
# 💰 SCHEMAS PARA PAGOS - AGREGAR EN schemas.py
# ============================================================================

class PagoBase(BaseModel):
    credito_id: int
    monto: float
    fecha_pago: date
    comprobante: str
    notas: Optional[str] = None

class PagoCreate(PagoBase):
    pass

class PagoUpdate(BaseModel):
    monto: Optional[float] = None
    fecha_pago: Optional[date] = None
    comprobante: Optional[str] = None
    notas: Optional[str] = None

class Pago(PagoBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

        

# ----------------------------------------
# 📌 Schemas para CContactoss
# ----------------------------------------
# En schemas.py, modifica la clase ContactoBase:
class ContactoBase(BaseModel):
    nombres: str
    apellidos: str
    categoria: str = 'otro'
    direccion: Optional[str] = None
    celular1: str  # Obligatorio
    celular2: Optional[str] = None  # Opcional
    email: Optional[EmailStr] = None
    notas: Optional[str] = None

class ContactoCreate(ContactoBase):
    pass

class ContactoUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    categoria: Optional[str] = None
    empresa: Optional[str] = None
    direccion: Optional[str] = None
    telefono1: Optional[str] = None
    celular1: Optional[str] = None
    telefono2: Optional[str] = None
    celular2: Optional[str] = None
    email: Optional[EmailStr] = None
    notas: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class Contacto(ContactoBase):
    id: int
    usuario_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)