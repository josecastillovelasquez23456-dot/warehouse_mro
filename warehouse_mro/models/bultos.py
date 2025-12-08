from warehouse_mro.models import db
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# 📦 MODELO PRINCIPAL: BULTOS
# ============================================================
class Bulto(db.Model):
    __tablename__ = "bultos"

    id = db.Column(db.Integer, primary_key=True)

    cantidad = db.Column(db.Integer, nullable=False)
    chofer = db.Column(db.String(120), nullable=False)
    placa = db.Column(db.String(20), nullable=False)

    # Fecha REAL de Perú
    fecha_hora = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Lima"))
    )

    observacion = db.Column(db.String(255))

    creado_en = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Lima"))
    )

    # Relación con conteos (Post-Registro)
    post_registros = db.relationship(
        "PostRegistro",
        backref="bulto",
        cascade="all, delete-orphan",
        lazy=True
    )

    @property
    def total_post_registros(self):
        return len(self.post_registros)

    @property
    def ultimo_post_registro(self):
        if not self.post_registros:
            return None
        return sorted(
            self.post_registros,
            key=lambda p: p.fecha_registro,
            reverse=True
        )[0]

    def __repr__(self):
        return f"<Bulto {self.id} - {self.placa}>"


# ============================================================
# 🔄 MODELO COMPLEMENTARIO: POST-REGISTRO
# ============================================================
class PostRegistro(db.Model):
    __tablename__ = "post_registro"

    id = db.Column(db.Integer, primary_key=True)

    bulto_id = db.Column(db.Integer, db.ForeignKey("bultos.id"), nullable=False)

    cantidad_sistema = db.Column(db.Integer, nullable=False)
    cantidad_real = db.Column(db.Integer, nullable=False)
    diferencia = db.Column(db.Integer, nullable=False)

    observacion = db.Column(db.String(255))
    registrado_por = db.Column(db.String(120))

    # Ahora siempre guarda la hora PERÚ
    fecha_registro = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Lima"))
    )

    def __repr__(self):
        return f"<PostRegistro {self.id} Bulto {self.bulto_id}>"

