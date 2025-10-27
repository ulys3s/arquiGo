# construyeseguro.py
# Autor: Ulises Jesús Pérez González
# Proyecto: ConstruyeSeguro - Plataforma de Autoconstrucción Asistida

from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)

# ----------- BASE DE DATOS -----------
DB_NAME = "construyeseguro.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            correo TEXT,
            presupuesto REAL,
            terreno REAL,
            clima TEXT,
            habitaciones INTEGER,
            materiales TEXT,
            experiencia TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            plano TEXT,
            manual TEXT,
            materiales TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )''')
    print("✅ Base de datos inicializada.")

# ----------- RUTA PRINCIPAL -----------
@app.route('/')
def index():
    return render_template('index.html')

# ----------- REGISTRO DE USUARIO -----------
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        presupuesto = request.form['presupuesto']
        terreno = request.form['terreno']
        clima = request.form['clima']
        habitaciones = request.form['habitaciones']
        materiales = request.form['materiales']
        experiencia = request.form['experiencia']

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('INSERT INTO usuarios (nombre, correo, presupuesto, terreno, clima, habitaciones, materiales, experiencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (nombre, correo, presupuesto, terreno, clima, habitaciones, materiales, experiencia))
        return redirect(url_for('dashboard', correo=correo))
    return render_template('registro.html')

# ----------- DASHBOARD DEL USUARIO -----------
@app.route('/dashboard/<correo>')
def dashboard(correo):
    with sqlite3.connect(DB_NAME) as conn:
        usuario = conn.execute("SELECT * FROM usuarios WHERE correo=?", (correo,)).fetchone()
    return render_template('dashboard.html', usuario=usuario)

# ----------- GENERADOR DE MANUAL CONSTRUCTIVO -----------
@app.route('/generar_manual/<correo>', methods=['POST'])
def generar_manual(correo):
    """Simulación de IA generando un manual constructivo"""
    with sqlite3.connect(DB_NAME) as conn:
        usuario = conn.execute("SELECT * FROM usuarios WHERE correo=?", (correo,)).fetchone()
        if usuario:
            nombre, presupuesto, clima, materiales = usuario[1], usuario[3], usuario[5], usuario[7]
            plano = f"Plano tipo generado para {nombre} en clima {clima} con materiales {materiales}."
            manual = f"1. Excava y cimenta de acuerdo al terreno.\n2. Usa {materiales} para muros y losas.\n3. Cuida ventilación e iluminación natural.\nPresupuesto estimado: ${presupuesto}"
            materiales_lista = f"{materiales}, cemento, varilla, pintura ecológica."
            conn.execute("INSERT INTO proyectos (usuario_id, plano, manual, materiales) VALUES (?, ?, ?, ?)",
                         (usuario[0], plano, manual, materiales_lista))
            conn.commit()
            return jsonify({"plano": plano, "manual": manual, "materiales": materiales_lista})
    return jsonify({"error": "No se encontró usuario."})

# ----------- VIDEOS EDUCATIVOS -----------
@app.route('/videos')
def videos():
    lista_videos = [
        {"titulo": "Cómo leer un plano arquitectónico", "url": "https://www.youtube.com/watch?v=example1"},
        {"titulo": "Ventilación y orientación solar", "url": "https://www.youtube.com/watch?v=example2"},
        {"titulo": "Cimentación segura para casas pequeñas", "url": "https://www.youtube.com/watch?v=example3"}
    ]
    return render_template('videos.html', videos=lista_videos)

# ----------- MARKETPLACE DE ARQUITECTOS -----------
@app.route('/arquitectos')
def arquitectos():
    lista_arquitectos = [
        {"nombre": "Arq. Sofía Ramírez", "especialidad": "Casas sostenibles", "precio": "$500 / consulta"},
        {"nombre": "Arq. Andrés López", "especialidad": "Diseño estructural", "precio": "$400 / validación"},
        {"nombre": "Arq. Alana Cruz", "especialidad": "Diseño rural", "precio": "$350 / plano base"}
    ]
    return render_template('arquitectos.html', arquitectos=lista_arquitectos)

# ----------- FINANCIAMIENTO -----------
@app.route('/financiamiento')
def financiamiento():
    opciones = [
        {"nombre": "Financiera HogarMX", "descripcion": "Créditos accesibles para ampliación y mejora de vivienda.", "tasa": "12% anual"},
        {"nombre": "Banco Solidario", "descripcion": "Apoyo a familias autoconstructoras con créditos flexibles.", "tasa": "10% anual"}
    ]
    return render_template('financiamiento.html', opciones=opciones)

# ----------- INICIO DEL SERVIDOR -----------
if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        init_db()
    app.run(debug=True)
