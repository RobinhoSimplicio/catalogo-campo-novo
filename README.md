# Catálogo de Loja em Python + Flask

Projeto simples de catálogo para compartilhar pelo WhatsApp.

## 1. Personalizar

Abra `app.py` e altere:

- `LOJA["nome"]`
- `LOJA["descricao"]`
- `LOJA["whatsapp"]`

O WhatsApp deve ficar no formato:
`5582999999999`

Depois altere os produtos dentro da lista `PRODUTOS`.

## 2. Colocar fotos

Coloque as imagens dos produtos em:

`static/img/`

e use o nome do arquivo no campo `imagem`.

Exemplo:
`"imagem": "camisa.jpg"`

## 3. Rodar no computador

No terminal:

```bash
pip install -r requirements.txt
python app.py
```

Depois abra:

`http://127.0.0.1:5000`

## 4. Publicar na internet

O projeto já inclui `render.yaml` e `Procfile` para facilitar a publicação em serviços compatíveis com Python.

Depois de publicar, você receberá um endereço público que poderá enviar pelo WhatsApp.

## Observação

Este modelo não possui banco de dados nem painel administrativo. Os produtos são cadastrados no arquivo `app.py`, o que deixa o projeto simples e fácil de hospedar.
