# Base declarativa compartida por todos los modelos ORM.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Clase base para mapear tablas SQL con SQLAlchemy ORM.
    pass
