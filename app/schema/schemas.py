from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import date, datetime
from typing import Optional, Dict, List
from typing import Union 
from datetime import date


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    username: str  # Nuevo campo

class UsuarioCreate(UsuarioBase):
    password: str
    salario: float = 0

class Usuario(UsuarioBase):
    id: int
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CategoriaBase(BaseModel):
    nombre: str
    tipo: str  # 'fijo', 'variable' o 'opcional'

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

class IngresoBase(BaseModel):
    valor: float
    fecha: date
    notas: Optional[str] = None

class IngresoCreate(IngresoBase):
    pass

class IngresoUpdate(BaseModel):
    valor: Optional[float] = None
    fecha: Optional[date] = None
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


 # Añade esto al inicio de tus imports

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
    categoria_mayor: Dict[str, Union[str, float]] = {  # Cambiado para aceptar string o float
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


   # app/schema/contrasenas_schemas.py


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





# Base para Cumpleaños
class CumpleanoBase(BaseModel):
    nombre_persona: str
    fecha_nacimiento: date
    telefono: Optional[str] = None
    email: Optional[str] = None
    relacion: Optional[str] = None
    notas: Optional[str] = None
    notificar_dias_antes: int = 7

# Para crear cumpleaños
class CumpleanoCreate(CumpleanoBase):
    pass

# Para actualizar cumpleaños
class CumpleanoUpdate(BaseModel):
    nombre_persona: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    relacion: Optional[str] = None
    notas: Optional[str] = None
    notificar_dias_antes: Optional[int] = None

# Para respuesta de cumpleaños
class Cumpleano(CumpleanoBase):
    id: int
    usuario_id: int
    created_at: datetime
    updated_at: datetime
    dias_hasta_cumpleanos: Optional[int] = None
    edad: Optional[int] = None
    
    class Config:
        from_attributes = True