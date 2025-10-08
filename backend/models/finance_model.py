# backend/models/finance_model.py
from database import db
from datetime import datetime

class FinanceData(db.Model):
    __tablename__ = 'finance_data'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assets = db.Column(db.JSON, nullable=True)
    liabilities = db.Column(db.JSON, nullable=True)
    snapshots = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "assets": self.assets,
            "liabilities": self.liabilities,
            "snapshots": self.snapshots,
            "updated_at": self.updated_at.isoformat()
        }
