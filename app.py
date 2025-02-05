import os
import qrcode
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, g, Response
from reportlab.pdfgen import canvas
import sqlite3
from datetime import datetime

# Configuración de la app Flask
app = Flask(__name__)
DATABASE = 'database.db'
QR_FOLDER = 'static/qr_codes'
os.makedirs(QR_FOLDER, exist_ok=True)

#Conexión a la base de datos
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Generar QR Code
def generate_qr(folio, name=None, tipo_discapacidad=None, vencimiento=None):
    base_url = "https://tarjetones.onrender.com"

    # Construye la URL basada en el folio
    qr_url = f"{base_url}/person/{folio}"

    # Genera el código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    # Guarda la imagen del QR
    qr_image_path = f"static/qr_codes/{folio}.png"
    qr_image = qr.make_image(fill="black", back_color="white")
    qr_image.save(qr_image_path)
    return qr_image_path

#Página principal
@app.route('/')
def index():
    db = get_db()
    persons = db.execute('SELECT * FROM persons').fetchall()
    return render_template('index.html', persons=persons)

#Agregar persona
@app.route('/add', methods=['GET', 'POST'])
def add_person():
    if request.method == 'POST':
        name = request.form['name']
        tipo_discapacidad = request.form['tipo_discapacidad']
        vencimiento = ''

        # Verificar tipo de discapacidad
        if tipo_discapacidad == 'Permanente':
            vencimiento = '2027-09-17'
        elif tipo_discapacidad == 'Temporal':
            vencimiento = request.form.get('vencimiento', '')
            if not vencimiento:
                return render_template('error.html', error_message="Debe ingresar una fecha de vencimiento para discapacidad temporal."), 400
        elif tipo_discapacidad == 'Familiar':
            anio_nacimiento = request.form.get('anio_nacimiento', '')
            if not anio_nacimiento.isdigit() or not (2022 <= int(anio_nacimiento) <= 2026):
                return render_template('error.html', error_message="Debe ingresar un año válido entre 2022 y 2026."), 400
            # Calcular vencimiento: año de nacimiento + 2 años
            anio_vencimiento = int(anio_nacimiento) + 2
            vencimiento = f"{anio_vencimiento}-09-17"

        # Insertar datos en la base de datos
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO persons (name, tipo_discapacidad, vencimiento) VALUES (?, ?, ?)",
                       (name, tipo_discapacidad, vencimiento))
        db.commit()

        # Generar QR Code
        folio = cursor.lastrowid
        generate_qr(folio, name, tipo_discapacidad, vencimiento)
        return redirect(url_for('index'))

    return render_template('add_person.html')

#Mostrar detalles de persona
@app.route('/person/<int:folio>')
def person_details(folio):
    try:
        db = get_db()  # Conexión a la base de datos
        # Cambia id por folio en la consulta
        person = db.execute('SELECT * FROM persons WHERE folio = ?', (folio,)).fetchone()

        if person is None:
            return render_template('error.html', error_message="Persona no encontrada.")

        return render_template('person_details.html', person=person)

    except sqlite3.OperationalError as e:
        print(f"Error en la base de datos: {e}")
        return render_template('error.html', error_message="Error en la base de datos.")
    except Exception as e:
        print(f"Error general: {e}")
        return render_template('error.html', error_message="Se produjo un error interno.")

#Exportar a CSV
@app.route('/export/csv')
def export_csv():
    db = get_db()
    persons = db.execute('SELECT * FROM persons').fetchall()

    output = []
    output.append(['Folio', 'Nombre', 'Tipo de Discapacidad', 'Vencimiento'])
    for person in persons:
        output.append([person['folio'], person['name'], person['tipo_discapacidad'], person['vencimiento']])

    # Crear respuesta HTTP con el CSV
    def generate():
        for row in output:
            yield ','.join(map(str, row)) + '\n'

    response = Response(generate(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=persons.csv'
    return response

#Exportar a PDF
@app.route('/export/pdf')
def export_pdf():
    db = get_db()
    persons = db.execute('SELECT * FROM persons').fetchall()

    pdf_path = os.path.join("static", "persons.pdf")
    c = canvas.Canvas(pdf_path)
    y = 800

    c.drawString(50, y, "Listado de Personas")
    y -= 30

    for person in persons:
        c.drawString(50, y, f"Folio: {person['folio']}, Nombre: {person['name']}, Tipo: {person['tipo_discapacidad']}, Vencimiento: {person['vencimiento']}")
        y -= 20
        if y < 50:
            c.showPage()
            y = 800

    c.save()
    return redirect(url_for('static', filename='persons.pdf'))

#Ejecutar la app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
