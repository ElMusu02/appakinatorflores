import math
from flask import Flask, render_template, request, session, redirect
from db import get_connection

app = Flask(__name__)
app.secret_key = "flores_secret"


ATRIBUTOS = {
    "color_flor": "¿De qué color es la flor?",
    "tipo_planta": "¿Qué tipo de planta es?",
    "espinas": "¿La planta tiene espinas?",
    "fruto_visible": "¿Tiene frutos visibles?",
    "forma_hoja": "¿Cómo es la forma de la hoja?",
    "aroma": "¿Tiene aroma perceptible?",
    "color_centro": "¿De qué color es el centro de la flor?",
    "agrupacion_flor": "¿Las flores aparecen agrupadas?",
    "hojas_perennes": "¿Mantiene hojas todo el año?",
    "habitat_humedo": "¿Crece en zonas húmedas?",
    "flor_colgante": "¿La flor cuelga hacia abajo?",
    "flores_por_tallo": "¿Cuántas flores aparecen por tallo?",
    "espinas_visibles": "¿Las espinas son visibles?"
}

def entropia_grupo(cantidades):

    total = sum(cantidades)

    if total == 0:
        return 0

    e = 0

    for cantidad in cantidades:

        if cantidad == 0:
            continue

        p = cantidad / total
        e -= p * math.log2(p)

    return e


def calcular_ganancia(distribucion):

    total = sum(cantidad for _, cantidad in distribucion)

    entropia_inicial = entropia_grupo([cantidad for _, cantidad in distribucion])

    entropia_esperada = 0

    for _, cantidad in distribucion:

        peso = cantidad / total

        # cada rama termina en un subconjunto
        # de tamaño "cantidad"
        entropia_esperada += peso * entropia_grupo([cantidad])

    ganancia = entropia_inicial - entropia_esperada

    return ganancia

def calcular_entropia(distribucion):

    total = sum(cantidad for _, cantidad in distribucion)

    if total == 0:
        return 0

    entropia = 0

    for _, cantidad in distribucion:

        p = cantidad / total

        if p > 0:
            entropia -= p * math.log2(p)

    return entropia


def obtener_mejor_pregunta(candidatos, preguntas_realizadas):

    if len(candidatos) <= 1:
        return None

    conn = get_connection()
    cur = conn.cursor()

    mejor_campo = None
    mejor_ganancia = -1

    ids_sql = str(tuple(candidatos))

    print("\n")
    print("========== NUEVA EVALUACION ==========")
    print("Flores candidatas:", len(candidatos))

    for campo in ATRIBUTOS.keys():

        if campo in preguntas_realizadas:
            continue

        cur.execute(f"""
            SELECT {campo}, COUNT(*)
            FROM flores
            WHERE id IN {ids_sql}
            AND {campo} IS NOT NULL
            GROUP BY {campo}
        """)

        distribucion = cur.fetchall()

        if len(distribucion) <= 1:
            continue

        ganancia = calcular_ganancia(distribucion)

        print(
            campo,
            "=>",
            distribucion,
            "ganancia:",
            round(ganancia, 4)
        )

        if ganancia > mejor_ganancia:
            mejor_ganancia = ganancia
            mejor_campo = campo

    cur.close()
    conn.close()

    print(
        "MEJOR PREGUNTA:",
        mejor_campo,
        "ganancia:",
        round(mejor_ganancia, 4)
    )

    return mejor_campo

@app.route("/")
def inicio():

    session.clear()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM flores")

    ids = [fila[0] for fila in cur.fetchall()]

    cur.close()
    conn.close()

    session["candidatos"] = ids
    session["preguntas_realizadas"] = []

    return render_template("index.html")


@app.route("/comenzar")
def comenzar():
    return redirect("/pregunta")


@app.route("/pregunta", methods=["GET", "POST"])
def pregunta():

    candidatos = session["candidatos"]

    if len(candidatos) == 1:
        return redirect("/resultado")

    if len(candidatos) == 0:
        return redirect("/resultado")

    # -------------------------
    # POST
    # -------------------------
    if request.method == "POST":

        campo = session["campo_actual"]
        respuesta = request.form["respuesta"]

        conn = get_connection()
        cur = conn.cursor()

        ids_sql = str(tuple(candidatos))

        cur.execute(
            f"""
            SELECT id
            FROM flores
            WHERE id IN {ids_sql}
            AND CAST({campo} AS TEXT) = %s
            """,
            (respuesta,)
        )

        nuevos = [fila[0] for fila in cur.fetchall()]

        cur.close()
        conn.close()

        session["candidatos"] = nuevos
        print("Respuesta:", respuesta)
        print("Candidatos restantes:", len(nuevos))

        return redirect("/pregunta")

    # -------------------------
    # GET
    # -------------------------

    campo = obtener_mejor_pregunta(
        candidatos,
        session["preguntas_realizadas"]
    )

    if campo is None:
        return redirect("/resultado")

    preguntas = session["preguntas_realizadas"]

    if campo not in preguntas:
        preguntas.append(campo)

    session["preguntas_realizadas"] = preguntas
    session["campo_actual"] = campo

    conn = get_connection()
    cur = conn.cursor()

    ids_sql = str(tuple(candidatos))

    cur.execute(f"""
        SELECT DISTINCT {campo}
        FROM flores
        WHERE id IN {ids_sql}
        AND {campo} IS NOT NULL
        ORDER BY {campo}
    """)

    opciones = [fila[0] for fila in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template(
        "pregunta.html",
        pregunta={
            "campo": campo,
            "texto": ATRIBUTOS[campo]
        },
        opciones=opciones,
        restantes=len(candidatos)
    )


@app.route("/resultado")
def resultado():

    candidatos = session["candidatos"]

    if len(candidatos) == 0:

        return render_template(
            "resultado.html",
            encontrado=False
        )

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            nombre_comun,
            nombre_cientifico,
            descripcion,
            color_flor,
            habitat
        FROM flores
        WHERE id = %s
    """, (candidatos[0],))

    flor = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "resultado.html",
        encontrado=True,
        flor=flor
    )


if __name__ == "__main__":
    app.run(debug=True)