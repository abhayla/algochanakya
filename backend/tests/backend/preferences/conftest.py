"""
SQLite compatibility fixtures for broker preferences tests.

Registers SQLAlchemy type compilers so that PostgreSQL-specific types
(JSONB, ARRAY, UUID, BigInteger, ENUM) work with SQLite in-memory test DB.
"""
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


@compiles(ARRAY, 'sqlite')
def compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(BigInteger, 'sqlite')
def compile_biginteger_sqlite(element, compiler, **kw):
    return "INTEGER"


@compiles(PgUUID, 'sqlite')
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(PgEnum, 'sqlite')
def compile_enum_sqlite(element, compiler, **kw):
    return compiler.visit_VARCHAR(element, **kw)
