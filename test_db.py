
from app.database import engine
from sqlalchemy import text
with engine.begin() as c:
    users = c.execute(text("SELECT id, correo, rol FROM usuario")).fetchall()
    print("Usuarios:", users)
    talleres = c.execute(text("SELECT id, nombre, usuario_id FROM taller")).fetchall()
    print("Talleres:", talleres)

