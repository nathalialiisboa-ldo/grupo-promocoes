# Exemplo do que colocar dentro do arquivo WSGI gerado pelo PythonAnywhere
# (aba "Web" -> link do arquivo WSGI, algo como
# /var/www/seuusuario_pythonanywhere_com_wsgi.py).
#
# O PythonAnywhere cria esse arquivo automaticamente com um exemplo grande
# cheio de comentários - apague tudo e cole isto no lugar, trocando
# "seuusuario" e "grupo-promocoes" pelos nomes reais da sua conta/pasta.

import sys

path = "/home/seuusuario/grupo-promocoes"
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application  # noqa: E402
