from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import bcrypt
from datetime import timedelta

# Configuração do Flask
app = Flask(__name__)
app.secret_key = "sua_chave_secreta"

# Tempo de inatividade antes de expirar a sessão (15 minutos)
app.permanent_session_lifetime = timedelta(minutes=15)

# Configuração do banco de dados MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'minas_cidadao'
}

# Criação das tabelas no banco
def criar_tabelas():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute(""" 
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        password VARCHAR(255) NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        modelo VARCHAR(100) NOT NULL,
        quantidade INT NOT NULL
    );
    """)
    connection.commit()
    cursor.close()
    connection.close()

criar_tabelas()

# Rota de login/cadastro
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        action = request.form['action']
        username = request.form['username']
        password = request.form['password']

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        if action == 'login':
            # Login
            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                session['username'] = username
                session.permanent = True  
                flash("Login realizado com sucesso!", "success")
                return redirect(url_for('pedidos'))  
            else:
                flash("Usuário ou senha incorretos.", "danger")
        elif action == 'register':
            # Cadastro
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s)", (username, hashed_password.decode('utf-8')))
            connection.commit()
            flash("Cadastro realizado com sucesso! Faça login.", "success")
        cursor.close()
        connection.close()

    return render_template('index.html')

@app.route('/pedidos', methods=['GET', 'POST'])
def pedidos():
    if 'username' not in session:
        flash("Você precisa estar logado para acessar essa página.", "danger")
        return redirect(url_for('index'))

    pedidos_list = []
    if request.method == 'POST':
        modelo = request.form.get('modelo')
        quantidade = request.form.get('quantidade')

        try:
            quantidade = int(quantidade)
            if quantidade <= 0:
                flash("A quantidade deve ser maior que zero.", "danger")
                return redirect(url_for('pedidos'))

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("INSERT INTO pedidos (modelo, quantidade) VALUES (%s, %s)", (modelo, quantidade))
            connection.commit()
            flash("Pedido inserido com sucesso!", "success")
        except ValueError:
            flash("Quantidade inválida. Deve ser um número inteiro.", "danger")
        except mysql.connector.Error as err:
            flash(f"Erro ao inserir no banco: {err}", "danger")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()


    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("SELECT id, modelo, quantidade FROM pedidos")
    pedidos_list = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('pedidos.html', pedidos=pedidos_list)


@app.route('/logout')
def logout():
    session.pop('username', None) 
    flash("Você foi desconectado.", "success")
    return redirect(url_for('index'))  


# Rota para buscar dados para o gráfico
@app.route('/api/dados_grafico')
def dados_grafico():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("SELECT modelo, SUM(quantidade) AS total FROM pedidos GROUP BY modelo")
    dados = cursor.fetchall()
    cursor.close()
    connection.close()

    # Preparar os dados para o JSON
    modelos = [row[0] for row in dados]
    quantidades = [row[1] for row in dados]

    return jsonify({'modelos': modelos, 'quantidades': quantidades})

# Rota para exibir o gráfico
@app.route('/grafico')
def grafico():
    return render_template('grafico.html')


@app.route('/editar_pedido/<int:id>', methods=['GET', 'POST'])
def editar_pedido(id):
    if 'username' not in session:
        flash("Você precisa estar logado para acessar essa página.", "danger")
        return redirect(url_for('index'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    if request.method == 'POST':
        modelo = request.form['modelo']
        quantidade = request.form['quantidade']

        # Atualizar o pedido no banco
        cursor.execute("""
            UPDATE pedidos 
            SET modelo = %s, quantidade = %s 
            WHERE id = %s
        """, (modelo, quantidade, id))
        connection.commit()
        cursor.close()
        connection.close()

        flash("Pedido atualizado com sucesso!", "success")
        return redirect(url_for('pedidos'))

    # Buscando  o pedido para preencher o formulário implementação que posso fazer mais pra frente para mudar 
    cursor.execute("SELECT modelo, quantidade FROM pedidos WHERE id = %s", (id,))
    pedido = cursor.fetchone()
    cursor.close()
    connection.close()

    if not pedido:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for('pedidos'))

    return render_template('editar_pedido.html', pedido=pedido, id=id)


@app.route('/deletar_pedido/<int:id>', methods=['POST'])
def deletar_pedido(id):
    if 'username' not in session:
        flash("Você precisa estar logado para acessar essa página.", "danger")
        return redirect(url_for('index'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM pedidos WHERE id = %s", (id,))
        connection.commit()
        flash("Pedido excluído com sucesso!", "success")
    except mysql.connector.Error as err:
        flash(f"Erro ao excluir o pedido: {err}", "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('pedidos'))



if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=8000) 
