---
description: >
  Pydantic schema conventions: from_attributes=True for ORM mapping, Decimal for financial fields,
  str+Enum for serializable enums, and separate Create/Update/Response schema pattern.
globs: ["backend/app/schemas/**/*.py"]
synthesized: true
private: false
---

# Pydantic Schema Conventions

## ORM Mapping

All response schemas that map to SQLAlchemy models MUST include `from_attributes = True`
in the model config. Use the `model_config` dict or `Config` inner class:

```python
class StrategyResponse(BaseModel):
    id: int
    name: str
    status: StrategyStatus

    model_config = {"from_attributes": True}
    # OR:
    class Config:
        from_attributes = True
```

Without this, SQLAlchemy model instances cannot be serialized to JSON by FastAPI.

## Financial Fields: Decimal Only

All prices, P&L values, quantities, and monetary amounts MUST use `Decimal`, not `float`.
This aligns with the `decimal-not-float-prices` rule.

```python
from decimal import Decimal

class StrategyLegCreate(BaseModel):
    strike_price: Decimal
    entry_price: Decimal
    lots: Decimal

# WRONG:
class StrategyLegCreate(BaseModel):
    strike_price: float  # NEVER for financial data
```

## Enum Pattern: str + Enum

Enums used in schemas MUST inherit from both `str` and `Enum` for JSON serialization:

```python
from enum import Enum

class ContractType(str, Enum):
    CE = "CE"
    PE = "PE"

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
```

Without the `str` mixin, enums serialize as `{"contract_type": "<ContractType.CE: 'CE'>"}` instead
of `{"contract_type": "CE"}`.

## Create / Update / Response Split

Each domain entity MUST have separate schemas for different operations:

| Schema Suffix | Purpose | Required Fields |
|---------------|---------|-----------------|
| `*Create` | POST body — all required fields for creation | All non-default fields required |
| `*Update` | PATCH/PUT body — optional fields for partial update | All fields `Optional[T] = None` |
| `*Response` | GET response — full entity with ID and metadata | Includes `id`, timestamps, `from_attributes=True` |

```python
class StrategyLegCreate(BaseModel):
    strike_price: Decimal
    contract_type: ContractType
    transaction_type: TransactionType

class StrategyLegUpdate(BaseModel):
    strike_price: Optional[Decimal] = None
    contract_type: Optional[ContractType] = None

class StrategyLegResponse(BaseModel):
    id: int
    strike_price: Decimal
    contract_type: ContractType
    transaction_type: TransactionType
    created_at: datetime

    model_config = {"from_attributes": True}
```

## Field Constraints

Use `Field()` for validation constraints on create/update schemas:

```python
class AutoPilotSettingsCreate(BaseModel):
    max_loss_percent: Decimal = Field(ge=0, le=100)
    max_positions: int = Field(ge=1, le=50)
    name: str = Field(min_length=1, max_length=100)
```

## MUST NOT

- MUST NOT use a single schema for both input and output — always split Create/Response
- MUST NOT use `float` for any financial field — use `Decimal`
- MUST NOT forget `from_attributes = True` on Response schemas — SQLAlchemy objects will fail to serialize
- MUST NOT use plain `Enum` without `str` mixin — JSON serialization will break
