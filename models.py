from tortoise import fields
from tortoise.models import Model
import datetime

class Client(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    positions = fields.ReverseRelation["Position"]
    margins = fields.ReverseRelation["Margin"]
    def __repr__(self):
        return f"Client(id={self.id}, name={self.name})"

class Position(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=10)
    quantity = fields.IntField(null=True)
    cost_basis = fields.FloatField()
    client = fields.ForeignKeyField("models.Client", related_name="positions")
    def __repr__(self):
        return f"<Position(id={self.id}, symbol={self.symbol}, quantity={self.quantity}, cost_basis={self.cost_basis})>"

class MarketData(Model):
    id = fields.IntField(pk=True)
    symbol = fields.CharField(max_length=50)
    current_price = fields.FloatField()
    timestamp = fields.DatetimeField(default=datetime.datetime.now)
    def __repr__(self):
        return f"<MarketData(id={self.id}, symbol={self.symbol}, current_price={self.current_price}, timestamp={self.timestamp})>"

class Margin(Model):
    id = fields.IntField(pk=True)  # Auto-increment primary key
    client = fields.ForeignKeyField("models.Client", related_name="margins", on_delete=fields.CASCADE)
    margin_requirement = fields.FloatField()
    loan = fields.FloatField()
    timestamp = fields.DatetimeField(default=datetime.datetime.now)