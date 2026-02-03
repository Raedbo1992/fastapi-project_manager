SET session_replication_role = 'replica';

-- Tabla: usuarios
;

CREATE UNIQUE INDEX ix_usuarios_username ON usuarios (username);
CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);
CREATE INDEX ix_usuarios_id ON usuarios (id);

-- Tabla: categorias
;

CREATE INDEX ix_categorias_id ON categorias (id);

-- Tabla: contrasenas
;

CREATE INDEX ix_contrasenas_id ON contrasenas (id);

-- Tabla: cumpleanos
;

CREATE INDEX ix_cumpleanos_id ON cumpleanos (id);

-- Tabla: ingresos
;

CREATE INDEX ix_ingresos_id ON ingresos (id);

-- Tabla: pendientes
;

CREATE INDEX ix_pendientes_id ON pendientes (id);

-- Tabla: gastos
;

CREATE INDEX ix_gastos_id ON gastos (id);

SET session_replication_role = 'origin';
