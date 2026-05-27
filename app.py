from flask import Flask, render_template, request, redirect, session, flash
from database import conectar, criar_tabelas
from flask import make_response
from xhtml2pdf import pisa
from io import BytesIO

app = Flask(__name__)
app.secret_key = "123456"

criar_tabelas()

# 🔐 CRIAR ADMIN AUTOMÁTICO
def criar_admin():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM usuario WHERE email=%s",
        ('admin@gmail.com',)
    )

    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO usuario (nome,email,senha,tipo)
            VALUES (%s,%s,%s,%s)
        """, ('Admin', 'admin@gmail.com', 'ResponsaveisCatequese123', 'admin'))

    conn.commit()
    conn.close()

criar_admin()


# 🏠 HOME
@app.route('/')
def home():

    if "usuario_id" not in session:
        return redirect('/login')

    if session["tipo"] == "admin":
        return redirect('/admin')

    return redirect('/catequista')


# 🔑 LOGIN
@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/autenticar', methods=['POST'])
def autenticar():

    email = request.form.get('email').strip()
    senha = request.form.get('senha').strip()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, tipo
        FROM usuario
        WHERE email=%s AND senha=%s
    """, (email, senha))

    usuario = cursor.fetchone()

    conn.close()

    if usuario:

        session['usuario_id'] = usuario[0]
        session['usuario_nome'] = usuario[1]
        session['tipo'] = usuario[2]

        if usuario[2] == "admin":
            return redirect('/admin')

        return redirect('/catequista')

    flash("Login inválido")
    return redirect('/login')


# 🚪 LOGOUT
@app.route('/deslogar')
def deslogar():
    session.clear()
    return redirect('/login')


@app.route('/admin')
def admin():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # TOTAL CRIANÇAS
    cursor.execute("SELECT COUNT(*) FROM crianca")
    total_criancas = cursor.fetchone()[0]

    # TOTAL CATEQUISTAS
    cursor.execute("""
        SELECT COUNT(*) FROM usuario
        WHERE tipo='catequista'
    """)
    total_catequistas = cursor.fetchone()[0]

    # TOTAL TURMAS
    cursor.execute("SELECT COUNT(*) FROM turma")
    total_turmas = cursor.fetchone()[0]

    # RANKING TURMAS
    cursor.execute("""
        SELECT turma.nome, COUNT(crianca.id) as total
        FROM turma
        LEFT JOIN crianca ON turma.id = crianca.turma_id
        GROUP BY turma.nome
        ORDER BY total DESC
    """)
    ranking_turmas = cursor.fetchall()

    turma_maior = ranking_turmas[0] if ranking_turmas else None

    conn.close()

    return render_template(
        'admin.html',
        total_criancas=total_criancas,
        total_catequistas=total_catequistas,
        total_turmas=total_turmas,
        ranking_turmas=ranking_turmas,
        turma_maior=turma_maior
    )


@app.route('/criancas')
def criancas():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT crianca.id, crianca.nome, turma.nome
        FROM crianca
        JOIN turma ON crianca.turma_id = turma.id
        ORDER BY crianca.nome
    """)
    criancas = cursor.fetchall()

    cursor.execute("SELECT id, nome FROM turma")
    turmas = cursor.fetchall()

    conn.close()

    return render_template('criancas.html',
                           criancas=criancas,
                           turmas=turmas)


@app.route('/catequistas')
def catequistas():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, email
        FROM usuario
        WHERE tipo='catequista'
        ORDER BY nome
    """)
    catequistas = cursor.fetchall()

    conn.close()

    return render_template('catequistas.html',
                           catequistas=catequistas)

@app.route('/turmas')
def turmas():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome
        FROM turma
        ORDER BY nome
    """)
    turmas = cursor.fetchall()

    conn.close()

    return render_template('turmas.html',
                           turmas=turmas)

@app.route('/admins')
def admins():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, email
        FROM usuario
        WHERE tipo='admin'
        ORDER BY nome
    """)
    admins = cursor.fetchall()

    conn.close()

    return render_template('admins.html',
                           admins=admins)

# ➕ CADASTRAR CATEQUISTA
@app.route('/cadastrar_catequista', methods=['POST'])
def cadastrar_catequista():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuario (nome,email,senha,tipo)
        VALUES (%s,%s,%s,'catequista')
    """, (
        request.form['nome'],
        request.form['email'],
        request.form['senha']
    ))

    conn.commit()
    conn.close()

    return redirect('/admin')

# ✏️ EDITAR CATEQUISTA
@app.route('/editar_catequista/<int:id>', methods=['GET', 'POST'])
def editar_catequista(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        cursor.execute("""
            UPDATE usuario
            SET nome=%s, email=%s, senha=%s
            WHERE id=%s
        """, (
            request.form['nome'],
            request.form['email'],
            request.form['senha'],
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/admin')

    cursor.execute("""
        SELECT id, nome, email, senha
        FROM usuario
        WHERE id=%s
    """, (id,))

    catequista = cursor.fetchone()

    conn.close()

    return render_template(
        'editar_catequista.html',
        catequista=catequista
    )


# ❌ EXCLUIR CATEQUISTA
@app.route('/excluir_catequista/<int:id>')
def excluir_catequista(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # REMOVE RELAÇÃO COM TURMAS
    cursor.execute("""
        DELETE FROM turma_catequista
        WHERE catequista_id=%s
    """, (id,))

    # REMOVE USUÁRIO
    cursor.execute("""
        DELETE FROM usuario
        WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ➕ CADASTRAR TURMA
@app.route('/cadastrar_turma', methods=['POST'])
def cadastrar_turma():

    nome = request.form.get('nome')
    catequistas = request.form.getlist('catequista_id')

    conn = conectar()
    cursor = conn.cursor()

    # CRIA TURMA
    cursor.execute("""
        INSERT INTO turma (nome)
        VALUES (%s)
        RETURNING id
    """, (nome,))

    turma_id = cursor.fetchone()[0]

    # RELACIONA CATEQUISTAS
    for catequista_id in catequistas:

        cursor.execute("""
            INSERT INTO turma_catequista
            (turma_id, catequista_id)
            VALUES (%s,%s)
        """, (turma_id, catequista_id))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ➕ CADASTRAR CRIANÇA
@app.route('/cadastrar_crianca', methods=['POST'])
def cadastrar_crianca():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO crianca (nome,turma_id)
        VALUES (%s,%s)
    """, (
        request.form['nome'],
        request.form['turma_id']
    ))

    conn.commit()
    conn.close()

    return redirect('/admin')


# 👩‍🏫 CATEQUISTA
@app.route('/catequista')
def catequista():

    usuario_id = session['usuario_id']

    conn = conectar()
    cursor = conn.cursor()

    # NOME
    cursor.execute("""
        SELECT nome
        FROM usuario
        WHERE id=%s
    """, (usuario_id,))

    catequista_nome = cursor.fetchone()[0]

    # TURMAS
    cursor.execute("""
        SELECT turma.id, turma.nome
        FROM turma
        INNER JOIN turma_catequista
        ON turma.id = turma_catequista.turma_id
        WHERE turma_catequista.catequista_id=%s
        ORDER BY turma.nome
    """, (usuario_id,))

    turmas = cursor.fetchall()

    turma_id = request.args.get('turma')

    criancas = []

    if turma_id:

        cursor.execute("""
            SELECT id, nome
            FROM crianca
            WHERE turma_id=%s
            ORDER BY nome
        """, (turma_id,))

        resultado = cursor.fetchall()

        for c in resultado:

            criancas.append({
                "id": c[0],
                "nome": c[1]
            })

    conn.close()

    return render_template(
        'catequista.html',
        catequista_nome=catequista_nome,
        turmas=turmas,
        criancas=criancas,
        turma_selecionada=turma_id
    )


# 📌 REGISTRAR PRESENÇA
@app.route('/registrar_presenca', methods=['POST'])
def registrar_presenca():

    data = request.form.get('data')
    usuario_id = session['usuario_id']

    conn = conectar()
    cursor = conn.cursor()

    # BUSCA TURMA DA CATEQUISTA
    cursor.execute("""
        SELECT turma.id
        FROM turma
        INNER JOIN turma_catequista
        ON turma.id = turma_catequista.turma_id
        WHERE turma_catequista.catequista_id=%s
    """, (usuario_id,))

    turma = cursor.fetchone()

    if not turma:
        conn.close()
        return redirect('/catequista')

    turma_id = turma[0]

    # VERIFICA SE JÁ EXISTE CHAMADA NESSE DIA
    cursor.execute("""

        SELECT presenca.id

        FROM presenca

        INNER JOIN crianca
        ON presenca.crianca_id = crianca.id

        WHERE crianca.turma_id=%s
        AND DATE(presenca.data)=DATE(%s)

    """, (
        turma_id,
        data
    ))

    chamada_existente = cursor.fetchone()

    # BLOQUEIA DUPLICAÇÃO
    if chamada_existente:

        conn.close()

        return '''
            <script>
                alert("A chamada dessa turma já foi registrada nesse dia!");
                window.location.href="/catequista";
            </script>
        '''

    # BUSCA CRIANÇAS
    cursor.execute("""
        SELECT id
        FROM crianca
        WHERE turma_id=%s
    """, (turma_id,))

    criancas = cursor.fetchall()

    # SALVA PRESENÇAS
    for c in criancas:

        crianca_id = c[0]

        status = request.form.get(f"status_{crianca_id}")
        justificativa = request.form.get(f"justificativa_{crianca_id}")

        if status:

            cursor.execute("""
                INSERT INTO presenca
                (crianca_id,data,status,justificativa)
                VALUES (%s,%s,%s,%s)
            """, (
                crianca_id,
                data,
                status,
                justificativa
            ))

    conn.commit()
    conn.close()

    return redirect('/catequista')
# 📊 RELATÓRIO
@app.route('/relatorio', methods=['GET', 'POST'])
def relatorio():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    relatorio_turmas = []
    grafico_faltas = []
    alertas = []

    if request.method == 'POST':

        mes = request.form.get('mes')

        cursor.execute("""
            SELECT id, nome
            FROM turma
            ORDER BY nome
        """)

        turmas = cursor.fetchall()

        for turma in turmas:

            turma_id = turma[0]
            turma_nome = turma[1]

            cursor.execute("""
                SELECT id, nome
                FROM crianca
                WHERE turma_id=%s
                ORDER BY nome
            """, (turma_id,))

            criancas = cursor.fetchall()

            dados_criancas = []

            for c in criancas:

                cursor.execute("""
                    SELECT status, justificativa
                    FROM presenca
                    WHERE crianca_id=%s
                    AND TO_CHAR(data, 'YYYY-MM')=%s
                """, (c[0], mes))

                registros = cursor.fetchall()

                presencas = 0
                faltas = 0
                justificativas = []

                for r in registros:

                    if r[0] == "Presente":
                        presencas += 1
                    else:
                        faltas += 1

                        if r[1]:
                            justificativas.append(r[1])

                total = presencas + faltas

                freq = round(
                    (presencas / total) * 100,
                    1
                ) if total > 0 else 0

                if freq < 50 and total > 0:

                    alertas.append({
                        "nome": c[1],
                        "turma": turma_nome,
                        "frequencia": freq,
                        "faltas": faltas
                    })

                dados_criancas.append({
                    "nome": c[1],
                    "presencas": presencas,
                    "faltas": faltas,
                    "frequencia": freq,
                    "justificativas":
                        " | ".join(justificativas)
                        if justificativas else "-"
                })

            relatorio_turmas.append({
                "turma": turma_nome,
                "dados": dados_criancas
            })

        # GRÁFICO
        for turma in relatorio_turmas:

            total_faltas = 0

            for aluno in turma["dados"]:
                total_faltas += aluno["faltas"]

            grafico_faltas.append({
                "turma": turma["turma"],
                "faltas": total_faltas
            })

        grafico_faltas = sorted(
            grafico_faltas,
            key=lambda x: x["faltas"],
            reverse=True
        )

        # =========================
        # GERAR PDF
        # =========================
        if request.form.get("gerar_pdf"):

            html = render_template(
                'relatorio_pdf.html',
                relatorio_turmas=relatorio_turmas,
                grafico_faltas=grafico_faltas,
                alertas=alertas
            )

            pdf = BytesIO()

            pisa.CreatePDF(
                src=html,
                dest=pdf
            )

            response = make_response(pdf.getvalue())

            response.headers['Content-Type'] = 'application/pdf'

            response.headers['Content-Disposition'] = (
                'attachment; filename=relatorio.pdf'
            )

            return response

    conn.close()

    return render_template(
        'relatorio.html',
        relatorio_turmas=relatorio_turmas,
        grafico_faltas=grafico_faltas,
        alertas=alertas
    )
# ✏️ EDITAR CRIANÇA
@app.route('/editar_crianca/<int:id>', methods=['GET', 'POST'])
def editar_crianca(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        cursor.execute("""
            UPDATE crianca
            SET nome=%s, turma_id=%s
            WHERE id=%s
        """, (
            request.form['nome'],
            request.form['turma_id'],
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/admin')

    cursor.execute("""
        SELECT *
        FROM crianca
        WHERE id=%s
    """, (id,))

    crianca = cursor.fetchone()

    cursor.execute("""
        SELECT id, nome
        FROM turma
    """)

    turmas = cursor.fetchall()

    conn.close()

    return render_template(
        'editar_crianca.html',
        crianca=crianca,
        turmas=turmas
    )


# ❌ EXCLUIR CRIANÇA
@app.route('/excluir_crianca/<int:id>')
def excluir_crianca(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM presenca
        WHERE crianca_id=%s
    """, (id,))

    cursor.execute("""
        DELETE FROM crianca
        WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ⚙️ CONFIGURAÇÕES
@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():

    if "usuario_id" not in session:
        return redirect('/login')

    usuario_id = session['usuario_id']

    conn = conectar()
    cursor = conn.cursor()

    if request.method == 'POST':

        email = request.form.get('email')
        senha = request.form.get('senha')

        cursor.execute("""
            UPDATE usuario
            SET email=%s, senha=%s
            WHERE id=%s
        """, (
            email,
            senha,
            usuario_id
        ))

        conn.commit()

        flash("Dados atualizados com sucesso!")

    cursor.execute("""
        SELECT nome, email
        FROM usuario
        WHERE id=%s
    """, (usuario_id,))

    usuario = cursor.fetchone()

    conn.close()

    return render_template(
        'configuracoes.html',
        usuario=usuario
    )

# ✏️ EDITAR TURMA
@app.route('/editar_turma/<int:id>', methods=['GET', 'POST'])
def editar_turma(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # SALVAR EDIÇÃO
    if request.method == 'POST':

        nome = request.form.get('nome')
        catequistas = request.form.getlist('catequista_id')

        # ATUALIZA NOME DA TURMA
        cursor.execute("""
            UPDATE turma
            SET nome=%s
            WHERE id=%s
        """, (nome, id))

        # REMOVE CATEQUISTAS ANTIGOS
        cursor.execute("""
            DELETE FROM turma_catequista
            WHERE turma_id=%s
        """, (id,))

        # ADICIONA NOVOS CATEQUISTAS
        for catequista_id in catequistas:

            cursor.execute("""
                INSERT INTO turma_catequista
                (turma_id, catequista_id)
                VALUES (%s,%s)
            """, (id, catequista_id))

        conn.commit()
        conn.close()

        return redirect('/admin')

    # PEGAR TURMA
    cursor.execute("""
        SELECT id, nome
        FROM turma
        WHERE id=%s
    """, (id,))

    turma = cursor.fetchone()

    # PEGAR TODOS OS CATEQUISTAS
    cursor.execute("""
        SELECT id, nome
        FROM usuario
        WHERE tipo='catequista'
        ORDER BY nome
    """)

    catequistas = cursor.fetchall()

    # PEGAR CATEQUISTAS DA TURMA
    cursor.execute("""
        SELECT catequista_id
        FROM turma_catequista
        WHERE turma_id=%s
    """, (id,))

    selecionados = [x[0] for x in cursor.fetchall()]

    conn.close()

    return render_template(
        'editar_turma.html',
        turma=turma,
        catequistas=catequistas,
        selecionados=selecionados
    )


# ❌ EXCLUIR TURMA
@app.route('/excluir_turma/<int:id>')
def excluir_turma(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # REMOVE PRESENÇAS DAS CRIANÇAS
    cursor.execute("""
        DELETE FROM presenca
        WHERE crianca_id IN (
            SELECT id
            FROM crianca
            WHERE turma_id=%s
        )
    """, (id,))

    # REMOVE RELAÇÃO DOS CATEQUISTAS
    cursor.execute("""
        DELETE FROM turma_catequista
        WHERE turma_id=%s
    """, (id,))

    # REMOVE CRIANÇAS
    cursor.execute("""
        DELETE FROM crianca
        WHERE turma_id=%s
    """, (id,))

    # REMOVE TURMA
    cursor.execute("""
        DELETE FROM turma
        WHERE id=%s
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/admin')

# 👁️ VISUALIZAR TURMA
@app.route('/visualizar_turma/<int:id>')
def visualizar_turma(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # PEGAR NOME DA TURMA
    cursor.execute("""
        SELECT nome
        FROM turma
        WHERE id=%s
    """, (id,))

    turma = cursor.fetchone()

    # PEGAR CATEQUISTAS DA TURMA
    cursor.execute("""
        SELECT usuario.nome
        FROM usuario
        INNER JOIN turma_catequista
        ON usuario.id = turma_catequista.catequista_id
        WHERE turma_catequista.turma_id=%s
        ORDER BY usuario.nome
    """, (id,))

    catequistas = cursor.fetchall()

    # PEGAR CRIANÇAS
    cursor.execute("""
        SELECT nome
        FROM crianca
        WHERE turma_id=%s
        ORDER BY nome
    """, (id,))

    criancas = cursor.fetchall()

    conn.close()

    return render_template(
        'visualizar_turma.html',
        turma=turma,
        catequistas=catequistas,
        criancas=criancas
    )

# =========================
# COLE NO FINAL DO app.py
# ANTES DO if __name__ == '__main__':
# =========================


# ➕ NOVO ADMIN
@app.route('/novo_admin', methods=['POST'])
def novo_admin():

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuario (nome,email,senha,tipo)
        VALUES (%s,%s,%s,'admin')
    """, (
        request.form['nome'],
        request.form['email'],
        request.form['senha']
    ))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ✏️ EDITAR ADMIN
@app.route('/editar_admin/<int:id>', methods=['GET', 'POST'])
def editar_admin(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    conn = conectar()
    cursor = conn.cursor()

    # SALVAR ALTERAÇÕES
    if request.method == 'POST':

        cursor.execute("""
            UPDATE usuario
            SET nome=%s,
                email=%s,
                senha=%s
            WHERE id=%s
            AND tipo='admin'
        """, (
            request.form['nome'],
            request.form['email'],
            request.form['senha'],
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/admin')

    # BUSCAR ADMIN
    cursor.execute("""
        SELECT id, nome, email, senha
        FROM usuario
        WHERE id=%s
        AND tipo='admin'
    """, (id,))

    admin = cursor.fetchone()

    # SE NÃO EXISTIR
    if not admin:

        conn.close()
        flash("Admin não encontrado.")
        return redirect('/admin')

    conn.close()

    return render_template(
        'editar_admin.html',
        admin=admin
    )


# ❌ EXCLUIR ADMIN
@app.route('/excluir_admin/<int:id>')
def excluir_admin(id):

    if session.get("tipo") != "admin":
        return redirect('/login')

    # NÃO DEIXA APAGAR A SI MESMO
    if id == session['usuario_id']:

        flash("Você não pode excluir seu próprio usuário.")
        return redirect('/admin')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM usuario
        WHERE id=%s
        AND tipo='admin'
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ✏️ EDITAR CHAMADA
@app.route('/editar_chamada', methods=['GET', 'POST'])
def editar_chamada():

    if session.get("tipo") != "catequista":
        return redirect('/login')

    usuario_id = session['usuario_id']

    conn = conectar()
    cursor = conn.cursor()

    # TURMAS DA CATEQUISTA
    cursor.execute("""
        SELECT turma.id, turma.nome
        FROM turma
        INNER JOIN turma_catequista
        ON turma.id = turma_catequista.turma_id
        WHERE turma_catequista.catequista_id=%s
    """, (usuario_id,))

    turmas = cursor.fetchall()

    registros = []
    data = None
    turma_id = None
    datas_chamadas = []

    # PEGAR DIAS QUE JÁ TEM CHAMADA
    cursor.execute("""

        SELECT DISTINCT DATE(presenca.data)

        FROM presenca

        INNER JOIN crianca
        ON presenca.crianca_id = crianca.id

        INNER JOIN turma
        ON crianca.turma_id = turma.id

        INNER JOIN turma_catequista
        ON turma.id = turma_catequista.turma_id

        WHERE turma_catequista.catequista_id=%s

        ORDER BY DATE(presenca.data) DESC

    """, (usuario_id,))

    datas = cursor.fetchall()

    for d in datas:
        datas_chamadas.append(str(d[0]))

    if request.method == 'POST':

        data = request.form.get('data')
        turma_id = request.form.get('turma_id')

        # =========================
        # EXCLUIR CHAMADA
        # =========================
        if request.form.get("excluir_chamada"):

            cursor.execute("""

                DELETE FROM presenca

                USING crianca

                WHERE presenca.crianca_id = crianca.id
                AND crianca.turma_id=%s
                AND DATE(presenca.data)=DATE(%s)

            """, (
                turma_id,
                data
            ))

            conn.commit()

            conn.close()

            return '''
                <script>
                    alert("Chamada excluída com sucesso!");
                    window.location.href="/editar_chamada";
                </script>
            '''

        # =========================
        # SALVAR ALTERAÇÕES
        # =========================
        if request.form.get("salvar"):

            for key in request.form:

                if key.startswith("status_"):

                    presenca_id = key.split("_")[1]

                    status = request.form.get(key)

                    justificativa = request.form.get(
                        f"justificativa_{presenca_id}"
                    )

                    cursor.execute("""
                        UPDATE presenca
                        SET status=%s,
                            justificativa=%s
                        WHERE id=%s
                    """, (
                        status,
                        justificativa,
                        presenca_id
                    ))

            conn.commit()

        # =========================
        # BUSCAR CHAMADA
        # =========================
        cursor.execute("""

            SELECT
                presenca.id,
                crianca.nome,
                presenca.status,
                presenca.justificativa

            FROM presenca

            INNER JOIN crianca
            ON presenca.crianca_id = crianca.id

            WHERE crianca.turma_id=%s
            AND DATE(presenca.data)=DATE(%s)

            ORDER BY crianca.nome

        """, (
            turma_id,
            data
        ))

        registros = cursor.fetchall()

    conn.close()

    return render_template(
        'editar_chamada.html',
        turmas=turmas,
        registros=registros,
        data=data,
        turma_id=turma_id,
        datas_chamadas=datas_chamadas
    )


if __name__ == '__main__':
    app.run(debug=True)
