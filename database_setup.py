import sqlite3

# Conexión a la base de datos
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Crear tabla persons
cursor.execute('''
CREATE TABLE IF NOT EXISTS persons (
    folio INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tipo_discapacidad TEXT NOT NULL,
    vencimiento TEXT NOT NULL
)
''')

conn.commit()
conn.close()
print("Base de datos y tabla 'persons' creadas correctamente.")
