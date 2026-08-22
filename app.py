import os
import sqlite3
from urllib.parse import quote

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.utils import secure_filename


# =====================================================
# CONFIGURAÇÃO
# =====================================================

app = Flask(__name__)

app.secret_key = "campo-novo-agrosolucoes"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "catalogo.db"
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "img"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    5 * 1024 * 1024
)


# =====================================================
# DADOS DA LOJA
# =====================================================

LOJA = {
    "nome": "Campo Novo - Agrosoluções",
    "descricao": "Tudo para o homem do campo",
    "whatsapp": "5582991246991",
}


# =====================================================
# ADMINISTRADOR
# =====================================================

ADMIN_USUARIO = "MAYA"

ADMIN_SENHA = "CampoNovo@2026"


# =====================================================
# EXTENSÕES DE IMAGEM
# =====================================================

EXTENSOES_PERMITIDAS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


# =====================================================
# BANCO DE DADOS
# =====================================================

def conectar():

    conexao = sqlite3.connect(
        DATABASE
    )

    conexao.row_factory = sqlite3.Row

    return conexao


# =====================================================
# VERIFICAR EXTENSÃO
# =====================================================

def extensao_permitida(nome):

    extensao = os.path.splitext(
        nome
    )[1].lower()

    return (
        extensao
        in EXTENSOES_PERMITIDAS
    )


# =====================================================
# SALVAR FOTO
# =====================================================

def salvar_foto(foto):

    if not foto or not foto.filename:
        return ""

    if not extensao_permitida(
        foto.filename
    ):
        return ""

    nome_original = secure_filename(
        foto.filename
    )

    if not nome_original:
        return ""

    extensao = os.path.splitext(
        nome_original
    )[1].lower()

    nome_arquivo = (
        f"produto_"
        f"{os.urandom(8).hex()}"
        f"{extensao}"
    )

    caminho = os.path.join(
        app.config["UPLOAD_FOLDER"],
        nome_arquivo
    )

    foto.save(caminho)

    return nome_arquivo


# =====================================================
# CRIAR / ATUALIZAR BANCO
# =====================================================

def criar_banco():

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )

    conexao = conectar()

    # -------------------------------------------------
    # TABELA DE PRODUTOS
    # -------------------------------------------------

    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS produtos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome TEXT NOT NULL,

            preco REAL NOT NULL DEFAULT 0,

            descricao TEXT DEFAULT '',

            categoria TEXT DEFAULT '',

            imagem TEXT DEFAULT '',

            promocao INTEGER NOT NULL DEFAULT 0,

            preco_promocional REAL DEFAULT NULL

        )
        """
    )

    conexao.commit()


    # -------------------------------------------------
    # MIGRAÇÃO DE BANCO ANTIGO
    # -------------------------------------------------

    colunas = conexao.execute(
        "PRAGMA table_info(produtos)"
    ).fetchall()

    nomes_colunas = {
        coluna["name"]
        for coluna in colunas
    }


    if "promocao" not in nomes_colunas:

        conexao.execute(
            """
            ALTER TABLE produtos
            ADD COLUMN promocao
            INTEGER NOT NULL DEFAULT 0
            """
        )


    if "preco_promocional" not in nomes_colunas:

        conexao.execute(
            """
            ALTER TABLE produtos
            ADD COLUMN preco_promocional
            REAL DEFAULT NULL
            """
        )


    conexao.commit()


    # -------------------------------------------------
    # PRODUTOS DE EXEMPLO
    # -------------------------------------------------

    quantidade = conexao.execute(
        "SELECT COUNT(*) FROM produtos"
    ).fetchone()[0]


    if quantidade == 0:

        produtos = [

            (
                "Produto Exemplo 1",
                49.90,
                "Descrição do produto.",
                "Diversos",
                "produto1.svg",
                0,
                None,
            ),

            (
                "Produto Exemplo 2",
                79.90,
                "Descrição do produto.",
                "Diversos",
                "produto2.svg",
                0,
                None,
            ),

            (
                "Produto Exemplo 3",
                99.90,
                "Descrição do produto.",
                "Diversos",
                "produto3.svg",
                0,
                None,
            ),

        ]


        conexao.executemany(
            """
            INSERT INTO produtos
            (
                nome,
                preco,
                descricao,
                categoria,
                imagem,
                promocao,
                preco_promocional
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            produtos
        )


        conexao.commit()


    conexao.close()


# =====================================================
# VERIFICAR ADMINISTRADOR
# =====================================================

def administrador_logado():

    return (
        session.get(
            "administrador"
        ) is True
    )


# =====================================================
# LOGIN
# =====================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def login():

    if administrador_logado():

        return redirect(
            url_for("admin")
        )


    if request.method == "POST":

        usuario = request.form.get(
            "usuario",
            ""
        ).strip()

        senha = request.form.get(
            "senha",
            ""
        )


        if (
            usuario.upper()
            == ADMIN_USUARIO
            and senha
            == ADMIN_SENHA
        ):

            session["administrador"] = True

            return redirect(
                url_for("admin")
            )


        flash(
            "Usuário ou senha incorretos."
        )


    return render_template(
        "login.html",
        loja=LOJA
    )


# =====================================================
# LOGOUT
# =====================================================

@app.route("/admin/logout")
def logout():

    session.pop(
        "administrador",
        None
    )

    return redirect(
        url_for("login")
    )


# =====================================================
# PÁGINA INICIAL
# =====================================================

@app.route("/")
def index():

    busca = request.args.get(
        "busca",
        ""
    ).strip()


    categoria = request.args.get(
        "categoria",
        ""
    ).strip()


    conexao = conectar()


    sql = """
        SELECT *
        FROM produtos
        WHERE 1=1
    """


    parametros = []


    # -------------------------------------------------
    # BUSCA
    # -------------------------------------------------

    if busca:

        sql += """
            AND (
                nome LIKE ?
                OR descricao LIKE ?
                OR categoria LIKE ?
            )
        """

        termo = f"%{busca}%"


        parametros.extend(
            [
                termo,
                termo,
                termo,
            ]
        )


    # -------------------------------------------------
    # CATEGORIA
    # -------------------------------------------------

    if categoria:

        sql += """
            AND categoria = ?
        """

        parametros.append(
            categoria
        )


    sql += """
        ORDER BY nome
    """


    produtos = conexao.execute(
        sql,
        parametros
    ).fetchall()


    # -------------------------------------------------
    # CATEGORIAS
    # -------------------------------------------------

    categorias = conexao.execute(
        """
        SELECT DISTINCT categoria
        FROM produtos
        WHERE categoria != ''
        ORDER BY categoria
        """
    ).fetchall()


    # -------------------------------------------------
    # OFERTA DA SEMANA
    # -------------------------------------------------

    promocao = conexao.execute(
        """
        SELECT *
        FROM produtos
        WHERE promocao = 1
        AND preco_promocional IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()


    conexao.close()


    return render_template(
        "index.html",

        loja=LOJA,

        produtos=produtos,

        categorias=categorias,

        busca=busca,

        categoria=categoria,

        promocao=promocao,

        administrador=administrador_logado()
    )


# =====================================================
# PÁGINA DO PRODUTO
# =====================================================

@app.route(
    "/produto/<int:produto_id>"
)
def produto(produto_id):

    conexao = conectar()


    item = conexao.execute(
        """
        SELECT *
        FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    ).fetchone()


    conexao.close()


    if not item:

        return (
            "Produto não encontrado",
            404
        )


    return render_template(
        "produto.html",

        loja=LOJA,

        produto=item
    )


# =====================================================
# INTERESSE PELO PRODUTO
# =====================================================

@app.route(
    "/interesse/<int:produto_id>"
)
def interesse(produto_id):

    conexao = conectar()


    item = conexao.execute(
        """
        SELECT *
        FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    ).fetchone()


    conexao.close()


    if not item:

        return redirect(
            url_for("index")
        )


    # -------------------------------------------------
    # SE ESTIVER EM PROMOÇÃO,
    # USA O PREÇO PROMOCIONAL
    # -------------------------------------------------

    if (
        item["promocao"]
        and item["preco_promocional"]
        is not None
    ):

        preco_usado = (
            item["preco_promocional"]
        )

    else:

        preco_usado = item["preco"]


    preco_formatado = (
        f"{preco_usado:.2f}"
        .replace(".", ",")
    )


    mensagem = (
        f"Olá! Tenho interesse "
        f"no produto: "
        f"{item['nome']} "
        f"- R$ {preco_formatado}"
    )


    link = (
        f"https://wa.me/"
        f"{LOJA['whatsapp']}"
        f"?text={quote(mensagem)}"
    )


    return redirect(link)


# =====================================================
# PAINEL ADMINISTRATIVO
# =====================================================

@app.route("/admin")
def admin():

    if not administrador_logado():

        return redirect(
            url_for("login")
        )


    conexao = conectar()


    produtos = conexao.execute(
        """
        SELECT *
        FROM produtos
        ORDER BY id DESC
        """
    ).fetchall()


    conexao.close()


    return render_template(
        "admin.html",

        loja=LOJA,

        produtos=produtos
    )


# =====================================================
# NOVO PRODUTO
# =====================================================

@app.route(
    "/admin/produto/novo",
    methods=["GET", "POST"]
)
def novo_produto():

    if not administrador_logado():

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()


        preco = request.form.get(
            "preco",
            "0"
        ).strip()


        descricao = request.form.get(
            "descricao",
            ""
        ).strip()


        categoria = request.form.get(
            "categoria",
            ""
        ).strip()


        foto = request.files.get(
            "foto"
        )


        if not nome:

            flash(
                "Informe o nome do produto."
            )

            return redirect(
                url_for("novo_produto")
            )


        try:

            preco = float(
                preco.replace(
                    ",",
                    "."
                )
            )

        except ValueError:

            flash(
                "Informe um preço válido."
            )

            return redirect(
                url_for("novo_produto")
            )


        imagem = ""


        if foto and foto.filename:

            imagem = salvar_foto(
                foto
            )


            if not imagem:

                flash(
                    "Formato de imagem inválido."
                )

                return redirect(
                    url_for("novo_produto")
                )


        conexao = conectar()


        conexao.execute(
            """
            INSERT INTO produtos
            (
                nome,
                preco,
                descricao,
                categoria,
                imagem,
                promocao,
                preco_promocional
            )
            VALUES (?, ?, ?, ?, ?, 0, NULL)
            """,
            (
                nome,
                preco,
                descricao,
                categoria,
                imagem,
            )
        )


        conexao.commit()

        conexao.close()


        flash(
            "Produto cadastrado com sucesso!"
        )


        return redirect(
            url_for("admin")
        )


    return render_template(
        "form_produto.html",

        loja=LOJA,

        produto=None
    )


# =====================================================
# EDITAR PRODUTO
# =====================================================

@app.route(
    "/admin/produto/<int:produto_id>/editar",
    methods=["GET", "POST"]
)
def editar_produto(produto_id):

    if not administrador_logado():

        return redirect(
            url_for("login")
        )


    conexao = conectar()


    produto = conexao.execute(
        """
        SELECT *
        FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    ).fetchone()


    if not produto:

        conexao.close()

        return (
            "Produto não encontrado",
            404
        )


    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()


        preco = request.form.get(
            "preco",
            "0"
        ).strip()


        descricao = request.form.get(
            "descricao",
            ""
        ).strip()


        categoria = request.form.get(
            "categoria",
            ""
        ).strip()


        foto = request.files.get(
            "foto"
        )


        if not nome:

            flash(
                "Informe o nome do produto."
            )

            conexao.close()

            return redirect(
                url_for(
                    "editar_produto",
                    produto_id=produto_id
                )
            )


        try:

            preco = float(
                preco.replace(
                    ",",
                    "."
                )
            )

        except ValueError:

            flash(
                "Informe um preço válido."
            )

            conexao.close()

            return redirect(
                url_for(
                    "editar_produto",
                    produto_id=produto_id
                )
            )


        imagem = produto["imagem"]


        if foto and foto.filename:

            nova_imagem = salvar_foto(
                foto
            )


            if not nova_imagem:

                flash(
                    "Formato de imagem inválido."
                )

                conexao.close()

                return redirect(
                    url_for(
                        "editar_produto",
                        produto_id=produto_id
                    )
                )


            imagem = nova_imagem


        conexao.execute(
            """
            UPDATE produtos

            SET
                nome = ?,
                preco = ?,
                descricao = ?,
                categoria = ?,
                imagem = ?

            WHERE id = ?
            """,
            (
                nome,
                preco,
                descricao,
                categoria,
                imagem,
                produto_id,
            )
        )


        conexao.commit()

        conexao.close()


        flash(
            "Produto atualizado com sucesso!"
        )


        return redirect(
            url_for("admin")
        )


    conexao.close()


    return render_template(
        "form_produto.html",

        loja=LOJA,

        produto=produto
    )


# =====================================================
# EXCLUIR PRODUTO
# =====================================================

@app.route(
    "/admin/produto/<int:produto_id>/excluir",
    methods=["POST"]
)
def excluir_produto(produto_id):

    if not administrador_logado():

        return redirect(
            url_for("login")
        )


    conexao = conectar()


    produto = conexao.execute(
        """
        SELECT imagem
        FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    ).fetchone()


    conexao.execute(
        """
        DELETE FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    )


    conexao.commit()

    conexao.close()


    if (
        produto
        and produto["imagem"]
    ):

        caminho = os.path.join(
            app.config["UPLOAD_FOLDER"],
            produto["imagem"]
        )


        if os.path.isfile(caminho):

            try:

                os.remove(caminho)

            except OSError:

                pass


    flash(
        "Produto excluído com sucesso!"
    )


    return redirect(
        url_for("admin")
    )


# =====================================================
# DEFINIR OFERTA DA SEMANA
# =====================================================

@app.route(
    "/admin/produto/<int:produto_id>/oferta",
    methods=["POST"]
)
def definir_oferta(produto_id):

    # -------------------------------------------------
    # PROTEÇÃO NO SERVIDOR
    # -------------------------------------------------

    if not administrador_logado():

        flash(
            "Acesso não autorizado."
        )

        return redirect(
            url_for("login")
        )


    preco_promocional = request.form.get(
        "preco_promocional",
        ""
    ).strip()


    # -------------------------------------------------
    # CONVERTER PREÇO
    # -------------------------------------------------

    try:

        preco_promocional = float(
            preco_promocional.replace(
                ",",
                "."
            )
        )

    except ValueError:

        flash(
            "Informe um preço promocional válido."
        )

        return redirect(
            url_for("admin")
        )


    if preco_promocional <= 0:

        flash(
            "O preço promocional deve ser maior que zero."
        )

        return redirect(
            url_for("admin")
        )


    conexao = conectar()


    # -------------------------------------------------
    # VERIFICAR PRODUTO
    # -------------------------------------------------

    produto = conexao.execute(
        """
        SELECT *
        FROM produtos
        WHERE id = ?
        """,
        (produto_id,)
    ).fetchone()


    if not produto:

        conexao.close()

        flash(
            "Produto não encontrado."
        )

        return redirect(
            url_for("admin")
        )


    # -------------------------------------------------
    # GARANTIR QUE O PREÇO PROMOCIONAL
    # NÃO SEJA MAIOR OU IGUAL AO PREÇO NORMAL
    # -------------------------------------------------

    if preco_promocional >= produto["preco"]:

        conexao.close()

        flash(
            "O preço promocional deve ser menor que o preço normal."
        )

        return redirect(
            url_for("admin")
        )


    # -------------------------------------------------
    # REMOVER OFERTA ANTERIOR
    # -------------------------------------------------

    conexao.execute(
        """
        UPDATE produtos

        SET
            promocao = 0,
            preco_promocional = NULL

        WHERE promocao = 1
        """
    )


    # -------------------------------------------------
    # DEFINIR NOVA OFERTA
    # -------------------------------------------------

    conexao.execute(
        """
        UPDATE produtos

        SET
            promocao = 1,
            preco_promocional = ?

        WHERE id = ?
        """,
        (
            preco_promocional,
            produto_id,
        )
    )


    conexao.commit()

    conexao.close()


    flash(
        f"{produto['nome']} foi definido como oferta da semana!"
    )


    return redirect(
        url_for("admin")
    )


# =====================================================
# REMOVER OFERTA
# =====================================================

@app.route(
    "/admin/produto/<int:produto_id>/remover-oferta",
    methods=["POST"]
)
def remover_oferta(produto_id):

    # -------------------------------------------------
    # PROTEÇÃO NO SERVIDOR
    # -------------------------------------------------

    if not administrador_logado():

        flash(
            "Acesso não autorizado."
        )

        return redirect(
            url_for("login")
        )


    conexao = conectar()


    conexao.execute(
        """
        UPDATE produtos

        SET
            promocao = 0,
            preco_promocional = NULL

        WHERE id = ?
        """,
        (produto_id,)
    )


    conexao.commit()

    conexao.close()


    flash(
        "Oferta removida com sucesso!"
    )


    return redirect(
        url_for("admin")
    )


# =====================================================
# INICIALIZAÇÃO DO BANCO
# =====================================================

criar_banco()


# =====================================================
# EXECUTAR APLICAÇÃO
# =====================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )