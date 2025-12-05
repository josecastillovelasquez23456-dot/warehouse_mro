from models import db
from datetime import datetime


# ============================================================
# 📦 MODELO PRINCIPAL: BULTOS
# ============================================================
class Bulto(db.Model):
    __tablename__ = "bultos"

    id = db.Column(db.Integer, primary_key=True)

    # Datos del registro inicial
    cantidad = db.Column(db.Integer, nullable=False)
    chofer = db.Column(db.String(120), nullable=False)
    placa = db.Column(db.String(20), nullable=False)

    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)  # fecha ingreso del tráiler
    observacion = db.Column(db.String(255))

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con Post-Registro (conteo real)
    post_registros = db.relationship(
        "PostRegistro",
        backref="bulto",
        cascade="all, delete-orphan",
        lazy=True
    )

    @property
    def total_post_registros(self):
        """Cuántas veces se ha contado este bulto."""
        return len(self.post_registros)

    @property
    def ultimo_post_registro(self):
        """Último conteo realizado (si existe)."""
        if not self.post_registros:
            return None
        return sorted(self.post_registros, key=lambda p: p.fecha_registro, reverse=True)[0]

    def __repr__(self):
        return f"<Bulto {self.id} - {self.placa}>"


# ============================================================
# 🔄 MODELO COMPLEMENTARIO: POST-REGISTRO DE BULTOS
# ============================================================
class PostRegistro(db.Model):
    __tablename__ = "post_registro"

    id = db.Column(db.Integer, primary_key=True)

    # Relación principal
    bulto_id = db.Column(db.Integer, db.ForeignKey("bultos.id"), nullable=False)

    # Datos de conteo
    cantidad_sistema = db.Column(db.Integer, nullable=False)
    cantidad_real = db.Column(db.Integer, nullable=False)
    diferencia = db.Column(db.Integer, nullable=False)

    observacion = db.Column(db.String(255))

    # Usuario que registró
    registrado_por = db.Column(db.String(120))

    # Fecha del post-registro
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PostRegistro {self.id} Bulto {self.bulto_id}>"
