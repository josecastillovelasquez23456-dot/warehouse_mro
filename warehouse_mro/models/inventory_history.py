# models/inventory_history.py
from datetime import datetime
from models import db

class InventoryHistory(db.Model):
    __tablename__ = "inventory_history"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.String(64), index=True, nullable=False)
    snapshot_name = db.Column(db.String(150), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    material_code = db.Column(db.String(50), index=True, nullable=False)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), index=True, nullable=False)
    libre_utilizacion = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<InventoryHistory {self.snapshot_name} - {self.material_code}>"
