"""
Servidor mínimo de opt-out. Precisa estar hospedado publicamente.
"""

from flask import Flask, request

from etapa4_supressao import suprimir_email
from token_utils import validar_token

app = Flask(__name__)


@app.route("/descadastro")
def descadastro():
    token = request.args.get("token", "")
    email = validar_token(token)

    if not email:
        return "<h3>Link inválido ou expirado.</h3>", 400

    suprimir_email(email, motivo="opt-out via link")
    return f"""
    <html><body style="font-family: Arial; text-align: center; padding: 60px;">
        <h2>Descadastro confirmado</h2>
        <p>O e-mail <strong>{email}</strong> não receberá mais nossas mensagens.</p>
    </body></html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)