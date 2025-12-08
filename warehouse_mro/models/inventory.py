from warehouse_mro.models import db
from datetime import datetime

class InventoryItem(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)

    material_code = db.Column(db.String(50), nullable=False)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False)

    libre_utilizacion = db.Column(db.Float, default=0)

    creado_en = db.Column(db.DateTime, default=datetime.now)

    @property
    def status(self):
        if self.libre_utilizacion <= 0:
            return "vacío"
        if self.libre_utilizacion <= 5:
            return "crítico"
        if self.libre_utilizacion <= 15:
            return "bajo"
        return "normal"
