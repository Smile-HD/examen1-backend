#!/usr/bin/env python3
"""
Script para corregir las URLs de QR de talleres en la base de datos.
Actualiza URLs de /payments/qr/ a /api/v1/payments/qr/
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener la URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL no está configurada en el archivo .env")
    exit(1)

# Crear engine y sesión
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def fix_qr_urls():
    """Actualiza las URLs de QR de talleres para que apunten al endpoint correcto."""
    db = SessionLocal()
    try:
        # Buscar todos los talleres con qr_image_url que comience con /payments/qr/
        result = db.execute(
            text("""
                SELECT id, nombre, qr_image_url 
                FROM taller 
                WHERE qr_image_url LIKE '/payments/qr/%'
            """)
        )
        
        talleres_to_update = result.fetchall()
        
        if not talleres_to_update:
            print("✓ No se encontraron talleres con URLs de QR que necesiten corrección.")
            return
        
        print(f"Encontrados {len(talleres_to_update)} talleres con URLs de QR a corregir:")
        
        for taller in talleres_to_update:
            taller_id, nombre, old_url = taller
            new_url = old_url.replace('/payments/qr/', '/api/v1/payments/qr/')
            
            print(f"  - Taller ID {taller_id} ({nombre})")
            print(f"    Antes: {old_url}")
            print(f"    Después: {new_url}")
            
            # Actualizar la URL
            db.execute(
                text("""
                    UPDATE taller 
                    SET qr_image_url = :new_url 
                    WHERE id = :taller_id
                """),
                {"new_url": new_url, "taller_id": taller_id}
            )
        
        db.commit()
        print(f"\n✓ Se actualizaron {len(talleres_to_update)} talleres correctamente.")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error al actualizar las URLs: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando corrección de URLs de QR de talleres...")
    print("-" * 60)
    fix_qr_urls()
    print("-" * 60)
    print("Proceso completado.")
