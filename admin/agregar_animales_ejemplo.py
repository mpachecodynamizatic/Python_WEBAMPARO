#!/usr/bin/env python3
"""
Script para agregar animales de ejemplo a la base de datos.
Ejecutar una sola vez: python admin/agregar_animales_ejemplo.py
"""
import os
import sys
import sqlite3

# Agregar el directorio admin al path para poder importar
sys.path.insert(0, os.path.dirname(__file__))

# Verificar si se está usando PostgreSQL
USE_POSTGRES = os.environ.get('DATABASE_URL') is not None

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    from urllib.parse import urlparse

    db_url = os.environ.get('DATABASE_URL')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    result = urlparse(db_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    conn.row_factory = psycopg2.extras.RealDictCursor
    placeholder = '%s'
    print("📊 Usando PostgreSQL")
else:
    db_path = os.path.join(os.path.dirname(__file__), 'protectora.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    placeholder = '?'
    print(f"📊 Usando SQLite: {db_path}")

cursor = conn.cursor()

# Lista completa de animales de ejemplo
animales_ejemplo = [
    # EN ADOPCIÓN - Perros
    ('Luna', 'perro', '2 años', 'Hembra', 'Mediano',
     'Luna es una perra mestiza muy cariñosa que busca un hogar lleno de amor. Es tranquila, obediente y se lleva bien con otros perros y niños.',
     None, 'adoption'),
    ('Max', 'perro', '3 años', 'Macho', 'Grande',
     'Max es un pastor alemán cruzado muy juguetón y enérgico. Le encanta pasear, correr y jugar. Ideal para familias activas con jardín.',
     None, 'adoption'),
    ('Rocky', 'perro', '5 años', 'Macho', 'Grande',
     'Rocky es un mastín muy leal y protector. Necesita una familia con experiencia en perros grandes. Es muy cariñoso y tranquilo en casa.',
     None, 'adoption'),
    ('Bella', 'perro', '1 año', 'Hembra', 'Pequeño',
     'Bella es una chihuahua mix pequeña y juguetona. Perfecta para pisos o casas pequeñas. Muy sociable, cariñosa y le encantan los mimos.',
     None, 'adoption'),
    ('Toby', 'perro', '6 años', 'Macho', 'Mediano',
     'Toby es un beagle adulto muy tranquilo y equilibrado. Ideal para personas mayores o familias que buscan un compañero calmado.',
     None, 'adoption'),
    ('Bruno', 'perro', '4 años', 'Macho', 'Grande',
     'Bruno es un golden retriever muy noble y cariñoso. Le encanta estar con su familia y es excelente con los niños. Muy educado y obediente.',
     None, 'adoption'),
    ('Coco', 'perro', '8 meses', 'Macho', 'Mediano',
     'Coco es un cachorro de bodeguero muy activo y juguetón. Necesita una familia que pueda dedicarle tiempo para adiestramiento y juegos.',
     None, 'adoption'),
    ('Nina', 'perro', '7 años', 'Hembra', 'Pequeño',
     'Nina es una yorkshire senior muy tranquila y mimosa. Busca un hogar donde pasar sus últimos años rodeada de amor y cuidados.',
     None, 'adoption'),
    ('Thor', 'perro', '2 años', 'Macho', 'Grande',
     'Thor es un husky siberiano muy enérgico. Necesita mucho ejercicio diario y una familia activa. Es muy sociable con perros y personas.',
     None, 'adoption'),
    ('Lola', 'perro', '3 años', 'Hembra', 'Mediano',
     'Lola es una cocker spaniel muy dulce y cariñosa. Le encanta jugar y dar paseos. Perfecta para familias con niños.',
     None, 'adoption'),

    # EN ADOPCIÓN - Gatos
    ('Misi', 'gato', '1 año', 'Hembra', 'Pequeño',
     'Misi es una gatita joven muy tranquila y mimosa. Perfecta para un hogar acogedor. Le encanta dormir al sol y recibir caricias.',
     None, 'adoption'),
    ('Simba', 'gato', '4 años', 'Macho', 'Mediano',
     'Simba es un gato naranja independiente pero cariñoso. Le gusta su espacio pero también los mimos. Perfecto compañero de hogar.',
     None, 'adoption'),
    ('Nala', 'gato', '2 años', 'Hembra', 'Pequeño',
     'Nala es una gatita siamesa muy elegante y cariñosa. Le encanta jugar y explorar. Se adapta bien a la vida en interior.',
     None, 'adoption'),
    ('Mía', 'gato', '3 años', 'Hembra', 'Mediano',
     'Mía es una gata tricolor muy cariñosa que busca un hogar tranquilo. Le gusta la rutina y los ambientes relajados.',
     None, 'adoption'),
    ('Bigotes', 'gato', '5 años', 'Macho', 'Mediano',
     'Bigotes es un gato blanco y negro muy tranquilo. Es perfecto para personas que buscan compañía sin mucho alboroto. Muy independiente.',
     None, 'adoption'),
    ('Canela', 'gato', '6 meses', 'Hembra', 'Pequeño',
     'Canela es una gatita bebé muy juguetona y curiosa. Necesita una familia paciente que le enseñe buenos hábitos. Muy sociable.',
     None, 'adoption'),
    ('Felix', 'gato', '8 años', 'Macho', 'Mediano',
     'Felix es un gato senior muy tranquilo y cariñoso. Busca un hogar donde vivir sus últimos años con paz y confort.',
     None, 'adoption'),
    ('Luna Gata', 'gato', '2 años', 'Hembra', 'Pequeño',
     'Luna es una gatita negra muy juguetona y activa. Le encanta trepar y explorar. Ideal para hogares con espacio.',
     None, 'adoption'),

    # EN ACOGIDA - Casa de acogida temporal
    ('Chispa', 'perro', '4 meses', 'Hembra', 'Pequeño',
     'Chispa es una cachorra que se está recuperando de un rescate. Necesita acogida temporal mientras encuentra familia definitiva.',
     None, 'foster'),
    ('Mora', 'gato', '3 meses', 'Hembra', 'Pequeño',
     'Mora es una gatita bebé que necesita familia de acogida. Es muy juguetona y está aprendiendo a socializar.',
     None, 'foster'),
    ('Dante', 'perro', '1 año', 'Macho', 'Mediano',
     'Dante está en acogida recuperándose de una operación. Es muy cariñoso y necesita un hogar temporal con cuidados especiales.',
     None, 'foster'),

    # ADOPTADOS - Historias de éxito
    ('Pelusa', 'gato', '2 años', 'Hembra', 'Pequeño',
     'Pelusa encontró su hogar definitivo! Ahora es una gatita muy feliz que disfruta de su nueva familia.',
     None, 'adopted'),
    ('Rex', 'perro', '3 años', 'Macho', 'Grande',
     'Rex fue adoptado por una familia maravillosa. Ahora disfruta de largos paseos diarios y tiene un gran jardín donde jugar.',
     None, 'adopted'),
    ('Cleo', 'gato', '4 años', 'Hembra', 'Mediano',
     'Cleo encontró un hogar perfecto donde es la reina de la casa. Su familia la adora y ella es muy feliz.',
     None, 'adopted'),
    ('Bobby', 'perro', '5 años', 'Macho', 'Grande',
     'Bobby fue adoptado hace 6 meses. Su familia nos cuenta que es un perro maravilloso y están muy contentos juntos.',
     None, 'adopted'),
]

print(f"\n📝 Preparando para insertar {len(animales_ejemplo)} animales de ejemplo...")

# Primero, verificar cuántos animales ya existen
cursor.execute('SELECT COUNT(*) as count FROM animals')
count_result = cursor.fetchone()
count_before = count_result[0] if USE_POSTGRES else count_result['count']
print(f"📊 Animales actuales en la BD: {count_before}")

# Insertar solo los que no existan (basándonos en el nombre)
insertados = 0
omitidos = 0

for animal in animales_ejemplo:
    nombre = animal[0]
    # Verificar si ya existe un animal con ese nombre
    cursor.execute(f'SELECT COUNT(*) as count FROM animals WHERE name = {placeholder}', (nombre,))
    exists_result = cursor.fetchone()
    exists = (exists_result[0] if USE_POSTGRES else exists_result['count']) > 0

    if not exists:
        try:
            cursor.execute(f'''
                INSERT INTO animals (name, type, age, gender, size, description, image, status)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            ''', animal)
            print(f"  ✅ Insertado: {nombre} ({animal[1]}, {animal[7]})")
            insertados += 1
        except Exception as e:
            print(f"  ❌ Error insertando {nombre}: {e}")
    else:
        print(f"  ⏭️  Omitido (ya existe): {nombre}")
        omitidos += 1

conn.commit()

# Verificar cuántos animales hay ahora
cursor.execute('SELECT COUNT(*) as count FROM animals')
count_result = cursor.fetchone()
count_after = count_result[0] if USE_POSTGRES else count_result['count']

print(f"\n📊 Resumen:")
print(f"  • Animales antes: {count_before}")
print(f"  • Nuevos insertados: {insertados}")
print(f"  • Omitidos (ya existían): {omitidos}")
print(f"  • Total ahora: {count_after}")

cursor.close()
conn.close()

print("\n✅ ¡Proceso completado!")
