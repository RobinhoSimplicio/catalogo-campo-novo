import os
from urllib.parse import quote
from uuid import uuid4

import sqlite3

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

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "campo-novo-agrosolucoes"
)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

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

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# =====================================================
# SUPABASE
# =====================================================

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY"
)

SUPABASE_ATIVO = bool(
    SUPABASE_URL and SUPABASE_KEY
)

supabase = None

if SUPABASE_ATIVO:

    from supabase import create_client

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
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
# EXTENSÕES
# =====================================================

EXTENSOES_PERMITIDAS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


# =====================================================
# SQLITE LOCAL
# =====================================================

def conectar_sqlite():

    conexao = sqlite3.connect(
        DATABASE
    )

    conexao.row_factory = sqlite3.Row

    return conexao


def criar_banco_local():

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )

    conexao = conectar_sqlite()

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

    conexao.close()


# =====================================================
# EXTENSÃO
# =====================================================

def extensao_permitida(nome):

    extensao = os.path.splitext(
        nome
    )[1].lower()

    return extensao in EXTENSOES_PERMITIDAS


# =====================================================
# MIME
# =====================================================

def descobrir_mime(nome):

    extensao = os.path.splitext(
        nome
    )[1].lower()

    tipos = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    return tipos.get(
        extensao,
        "application/octet-stream"
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
        f"{uuid4().hex}"
        f"{extensao}"
    )

    # -------------------------------------------------
    # SUPABASE
    # -------------------------------------------------

    if SUPABASE_ATIVO:

        try:

            conteudo = foto.read()

            caminho_storage = (
                f"produtos/{nome_arquivo}"
            )

            supabase.storage \
                .from_("produtos") \
                .upload(
                    caminho_storage,
                    conteudo,
                    {
                        "content-type":
                            descobrir_mime(
                                nome_arquivo
                            ),
                        "upsert": "true",
                    }
                )

            url_publica = (
                supabase.storage
                .from_("produtos")
                .get_public_url(
                    caminho_storage
                )
            )

            return url_publica

        except Exception as erro:

            print(
                "Erro ao enviar imagem "
                "para o Supabase:",
                erro
            )

            return ""


    # -------------------------------------------------
    # SQLITE / LOCAL
    # -------------------------------------------------

    caminho = os.path.join(
        app.config["UPLOAD_FOLDER"],
        nome_arquivo
    )

    try:

        foto.save(caminho)

    except Exception as erro:

        print(
            "Erro ao salvar imagem:",
            erro
        )

        return ""

    return nome_arquivo


# =====================================================
# EXCLUIR FOTO DO SUPABASE
# =====================================================

def excluir_foto_storage(url):

    if not SUPABASE_ATIVO:
        return

    if not url:
        return

    try:

        marcador = "/storage/v1/object/public/produtos/"

        if marcador not in url:
            return

        caminho = url.split(
            marcador,
            1
        )[1]

        supabase.storage \
            .from_("produtos") \
            .remove(
                [caminho]
            )

    except Exception as erro:

        print(
            "Erro ao excluir imagem:",
            erro
        )


# =====================================================
# AUTENTICAÇÃO
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

            session[
                "administrador"
            ] = True

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


    # =================================================
    # SUPABASE
    # =================================================

    if SUPABASE_ATIVO:

        consulta = (
            supabase
            .table("produtos")
            .select("*")
        )

        if busca:

            termo = (
                f"%{busca}%"
            )

            consulta = consulta.or_(
                f"nome.ilike.{termo},"
                f"descricao.ilike.{termo},"
                f"categoria.ilike.{termo}"
            )

        if categoria:

            consulta = consulta.eq(
                "categoria",
                categoria
            )

        resultado = (
            consulta
            .order(
                "nome"
            )
            .execute()
        )

        produtos = (
            resultado.data
            or []
        )


        resultado_categorias = (
            supabase
            .table("produtos")
            .select("categoria")
            .neq("categoria", "")
            .execute()
        )

        categorias_lista = [
            item["categoria"]
            for item
            in (
                resultado_categorias.data
                or []
            )
            if item.get("categoria")
        ]

        categorias = [
            {"categoria": categoria}
            for categoria
            in sorted(
                set(categorias_lista)
            )
        ]


        resultado_promocao = (
            supabase
            .table("produtos")
            .select("*")
            .eq(
                "promocao",
                True
            )
            .not_.is_(
                "preco_promocional",
                "null"
            )
            .order(
                "id",
                desc=True
            )
            .limit(1)
            .execute()
        )

        promocao = (
            resultado_promocao.data[0]
            if resultado_promocao.data
            else None
        )


    # =================================================
    # SQLITE LOCAL
    # =================================================

    else:

        criar_banco_local()

        conexao = conectar_sqlite()

        sql = """
            SELECT *
            FROM produtos
            WHERE 1=1
        """

        parametros = []

        if busca:

            sql += """
                AND (
                    nome LIKE ?
                    OR descricao LIKE ?
                    OR categoria LIKE ?
                )
            """

            termo = (
                f"%{busca}%"
            )

            parametros.extend(
                [
                    termo,
                    termo,
                    termo,
                ]
            )

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

        categorias = conexao.execute(
            """
            SELECT DISTINCT categoria
            FROM produtos
            WHERE categoria != ''
            ORDER BY categoria
            """
        ).fetchall()

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

    if SUPABASE_ATIVO:

        resultado = (
            supabase
            .table("produtos")
            .select("*")
            .eq(
                "id",
                produto_id
            )
            .limit(1)
            .execute()
        )

        item = (
            resultado.data[0]
            if resultado.data
            else None
        )

    else:

        conexao = conectar_sqlite()

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
# INTERESSE
# =====================================================

@app.route(
    "/interesse/<int:produto_id>"
)
def interesse(produto_id):

    if SUPABASE_ATIVO:

        resultado = (
            supabase
            .table("produtos")
            .select("*")
            .eq(
                "id",
                produto_id
            )
            .limit(1)
            .execute()
        )

        item = (
            resultado.data[0]
            if resultado.data
            else None
        )

    else:

        conexao = conectar_sqlite()

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
        f"{float(preco_usado):.2f}"
        .replace(
            ".",
            ","
        )
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
# ADMIN
# =====================================================

@app.route("/admin")
def admin():

    if not administrador_logado():

        return redirect(
            url_for("login")
        )

    if SUPABASE_ATIVO:

        resultado = (
            supabase
            .table("produtos")
            .select("*")
            .order(
                "id",
                desc=True
            )
            .execute()
        )

        produtos = (
            resultado.data
            or []
        )

    else:

        criar_banco_local()

        conexao = conectar_sqlite()

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
                    "Não foi possível salvar a imagem."
                )

                return redirect(
                    url_for("novo_produto")
                )

        if SUPABASE_ATIVO:

            try:

                supabase \
                    .table("produtos") \
                    .insert(
                        {
                            "nome": nome,
                            "preco": preco,
                            "descricao": descricao,
                            "categoria": categoria,
                            "imagem": imagem,
                            "promocao": False,
                            "preco_promocional": None,
                        }
                    ) \
                    .execute()

            except Exception as erro:

                print(
                    "Erro ao cadastrar produto:",
                    erro
                )

                if imagem:
                    excluir_foto_storage(
                        imagem
                    )

                flash(
                    "Erro ao cadastrar produto."
                )

                return redirect(
                    url_for("novo_produto")
                )

        else:

            criar_banco_local()

            conexao = conectar_sqlite()

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

    if SUPABASE_ATIVO:

        resultado = (
            supabase
            .table("produtos")
            .select("*")
            .eq(
                "id",
                produto_id
            )
            .limit(1)
            .execute()
        )

        produto = (
            resultado.data[0]
            if resultado.data
            else None
        )

    else:

        criar_banco_local()

        conexao = conectar_sqlite()

        produto = conexao.execute(
            """
            SELECT *
            FROM produtos
            WHERE id = ?
            """,
            (produto_id,)
        ).fetchone()

        conexao.close()

    if not produto:

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

            return redirect(
                url_for(
                    "editar_produto",
                    produto_id=produto_id
                )
            )

        imagem = produto.get(
            "imagem",
            ""
        )

        imagem_antiga = imagem

        if foto and foto.filename:

            nova_imagem = salvar_foto(
                foto
            )

            if not nova_imagem:

                flash(
                    "Não foi possível salvar a nova imagem."
                )

                return redirect(
                    url_for(
                        "editar_produto",
                        produto_id=produto_id
                    )
                )

            imagem = nova_imagem

        if SUPABASE_ATIVO:

            try:

                supabase \
                    .table("produtos") \
                    .update(
                        {
                            "nome": nome,
                            "preco": preco,
                            "descricao": descricao,
                            "categoria": categoria,
                            "imagem": imagem,
                        }
                    ) \
                    .eq(
                        "id",
                        produto_id
                    ) \
                    .execute()

                if (
                    imagem != imagem_antiga
                    and imagem_antiga
                ):

                    excluir_foto_storage(
                        imagem_antiga
                    )

            except Exception as erro:

                print(
                    "Erro ao editar produto:",
                    erro
                )

                if (
                    imagem != imagem_antiga
                    and imagem
                ):

                    excluir_foto_storage(
                        imagem
                    )

                flash(
                    "Erro ao atualizar produto."
                )

                return redirect(
                    url_for(
                        "editar_produto",
                        produto_id=produto_id
                    )
                )

        else:

            criar_banco_local()

            conexao = conectar_sqlite()

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

    if SUPABASE_ATIVO:

        resultado = (
            supabase
            .table("produtos")
            .select("imagem")
            .eq(
                "id",
                produto_id
            )
            .limit(1)
            .execute()
        )

        produto = (
            resultado.data[0]
            if resultado.data
            else None
        )

        (
            supabase
            .table("produtos")
            .delete()
            .eq(
                "id",
                produto_id
            )
            .execute()
        )

        if produto:

            imagem = produto.get(
                "imagem"
            )

            if imagem:

                excluir_foto_storage(
                    imagem
                )

    else:

        criar_banco_local()

        conexao = conectar_sqlite()

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
# OFERTA DA SEMANA
# =====================================================

@app.route(
    "/admin/produto/<int:produto_id>/oferta",
    methods=["POST"]
)
def definir_oferta(produto_id):

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

    if SUPABASE_ATIVO:

        resultado = (
            supabase
            .table("produtos")
            .select("*")
            .eq(
                "id",
                produto_id
            )
            .limit(1)
            .execute()
        )

        produto = (
            resultado.data[0]
            if resultado.data
            else None
        )

        if not produto:

            flash(
                "Produto não encontrado."
            )

            return redirect(
                url_for("admin")
            )

        if preco_promocional >= float(
            produto["preco"]
        ):

            flash(
                "O preço promocional deve ser menor que o preço normal."
            )

            return redirect(
                url_for("admin")
            )

        (
            supabase
            .table("produtos")
            .update(
                {
                    "promocao": False,
                    "preco_promocional": None,
                }
            )
            .eq(
                "promocao",
                True
            )
            .execute()
        )

        (
            supabase
            .table("produtos")
            .update(
                {
                    "promocao": True,
                    "preco_promocional":
                        preco_promocional,
                }
            )
            .eq(
                "id",
                produto_id
            )
            .execute()
        )

    else:

        criar_banco_local()

        conexao = conectar_sqlite()

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

        if preco_promocional >= produto["preco"]:

            conexao.close()

            flash(
                "O preço promocional deve ser menor que o preço normal."
            )

            return redirect(
                url_for("admin")
            )

        conexao.execute(
            """
            UPDATE produtos

            SET
                promocao = 0,
                preco_promocional = NULL

            WHERE promocao = 1
            """
        )

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
        "Oferta da semana definida com sucesso!"
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

    if not administrador_logado():

        flash(
            "Acesso não autorizado."
        )

        return redirect(
            url_for("login")
        )

    if SUPABASE_ATIVO:

        (
            supabase
            .table("produtos")
            .update(
                {
                    "promocao": False,
                    "preco_promocional": None,
                }
            )
            .eq(
                "id",
                produto_id
            )
            .execute()
        )

    else:

        criar_banco_local()

        conexao = conectar_sqlite()

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
# INICIALIZAÇÃO
# =====================================================

if not SUPABASE_ATIVO:

    criar_banco_local()


# =====================================================
# EXECUTAR
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