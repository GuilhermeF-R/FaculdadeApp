import sys
import os
import webbrowser
import json
import sqlite3
# pylint: disable=no-name-in-module
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidget,
    QPushButton, QLineEdit, QTabWidget, QFileDialog, QMessageBox,
    QInputDialog, QLabel, QListWidgetItem, QHBoxLayout,
    QComboBox, QDialog, QFormLayout, QDialogButtonBox, QTextBrowser
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont

#-------------------------------------imports---------------------------------------

# Database setup
def criar_banco_dados():
    try:
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            modulo TEXT,
            status TEXT
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER,
            tipo TEXT,
            nome TEXT,
            caminho TEXT,
            is_divisao BOOLEAN DEFAULT 0,
            ordem INTEGER DEFAULT 0,
            FOREIGN KEY (materia_id) REFERENCES materias(id)
        )''')
        
        conn.commit()
        print("Banco de dados criado/verificado com sucesso!")
    except Exception as e:
        print(f"Erro ao criar banco de dados: {e}")
    finally:
        conn.close()

criar_banco_dados()

class Conteudo:
    def __init__(self, nome="", caminho="", tipo="", is_divisao=False, ordem=0):
        self.nome = nome
        self.caminho = caminho
        self.tipo = tipo
        self.is_divisao = is_divisao
        self.ordem = ordem

    def __str__(self):
        if self.is_divisao:
            return f"------------------- {self.nome} -------------------"
        return f"{self.nome} | {self.caminho}"

class Materia:
    def __init__(self, id=None, nome="", modulo="", status="Em andamento"):
        self.id = id
        self.nome = nome
        self.modulo = modulo
        self.status = status
        self.conteudos_livros = []
        self.conteudos_videos = []
        self.aulas_ao_vivo = []

    def salvar(self):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        if self.id is None:
            cursor.execute(
                'INSERT INTO materias (nome, modulo, status) VALUES (?, ?, ?)',
                (self.nome, self.modulo, self.status)
            )
            self.id = cursor.lastrowid
        else:
            cursor.execute(
                'UPDATE materias SET nome=?, modulo=?, status=? WHERE id=?',
                (self.nome, self.modulo, self.status, self.id)
            )
        
        conn.commit()
        conn.close()
    
    def carregar_conteudos(self):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        self.conteudos_livros = []
        self.conteudos_videos = []
        self.aulas_ao_vivo = []
        
        # Load books/documents
        cursor.execute('SELECT nome, caminho, tipo, is_divisao, ordem FROM conteudos WHERE materia_id=? AND tipo="livro" ORDER BY ordem', (self.id,))
        for nome, caminho, tipo, is_divisao, ordem in cursor.fetchall():
            self.conteudos_livros.append(Conteudo(nome, caminho, tipo, is_divisao, ordem))
        
        # Load videos
        cursor.execute('SELECT nome, caminho, tipo, is_divisao, ordem FROM conteudos WHERE materia_id=? AND tipo="video" ORDER BY ordem', (self.id,))
        for nome, caminho, tipo, is_divisao, ordem in cursor.fetchall():
            self.conteudos_videos.append(Conteudo(nome, caminho, tipo, is_divisao, ordem))
        
        # Load live classes
        cursor.execute('SELECT nome, caminho, ordem FROM conteudos WHERE materia_id=? AND tipo="aula" ORDER BY ordem', (self.id,))
        for nome, caminho, ordem in cursor.fetchall():
            self.aulas_ao_vivo.append(Conteudo(nome, caminho, 'aula', False, ordem))
        
        conn.close()
    
    def adicionar_conteudo(self, conteudo):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        try:
            # Get max order for this type
            cursor.execute('SELECT MAX(ordem) FROM conteudos WHERE materia_id=? AND tipo=?', (self.id, conteudo.tipo))
            max_ordem = cursor.fetchone()[0] or 0
            
            cursor.execute(
                'INSERT INTO conteudos (materia_id, tipo, nome, caminho, is_divisao, ordem) VALUES (?, ?, ?, ?, ?, ?)',
                (self.id, conteudo.tipo, conteudo.nome, conteudo.caminho, conteudo.is_divisao, max_ordem + 1)
            )
            
            conn.commit()
        except Exception as e:
            print(f"Erro ao adicionar conteúdo: {e}")
        finally:
            conn.close()
        
        self.carregar_conteudos()  # Atualiza a lista de conteúdos
    
    def atualizar_ordem_conteudos(self, tipo, conteudos_ordenados):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        for ordem, conteudo in enumerate(conteudos_ordenados):
            if conteudo.tipo == 'aula':
                cursor.execute(
                    'UPDATE conteudos SET ordem=? WHERE materia_id=? AND tipo=? AND nome=? AND caminho=?',
                    (ordem, self.id, tipo, conteudo.nome, conteudo.caminho)
                )
            else:
                cursor.execute(
                    'UPDATE conteudos SET ordem=? WHERE materia_id=? AND tipo=? AND nome=? AND is_divisao=?',
                    (ordem, self.id, tipo, conteudo.nome, conteudo.is_divisao)
                )
        
        conn.commit()
        conn.close()
        self.carregar_conteudos()
    
    def remover_conteudo(self, conteudo):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        if conteudo.tipo == 'aula':
            cursor.execute('DELETE FROM conteudos WHERE materia_id=? AND tipo="aula" AND nome=? AND caminho=?',
                          (self.id, conteudo.nome, conteudo.caminho))
        else:
            cursor.execute('DELETE FROM conteudos WHERE materia_id=? AND tipo=? AND nome=? AND is_divisao=?',
                        (self.id, conteudo.tipo, conteudo.nome, 1 if conteudo.is_divisao else 0))
        
        conn.commit()
        conn.close()
        self.carregar_conteudos()
    
    def adicionar_divisao(self, tipo, nome="Div"):
        divisao = Conteudo(nome=nome, tipo=tipo, is_divisao=True)
        self.adicionar_conteudo(divisao)
    
    @classmethod
    def carregar_todas(cls):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, nome, modulo, status FROM materias ORDER BY nome')
        materias = []
        for id, nome, modulo, status in cursor.fetchall():
            materia = cls(id, nome, modulo, status)
            materia.carregar_conteudos()
            materias.append(materia)
        
        conn.close()
        return materias
    
    @classmethod
    def remover_por_id(cls, id):
        conn = sqlite3.connect('material.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM conteudos WHERE materia_id=?', (id,))
        cursor.execute('DELETE FROM materias WHERE id=?', (id,))
        
        conn.commit()
        conn.close()
    
    def __str__(self):
        return f"{self.nome} ({self.modulo}) - {self.status}"

class EditarMateriaDialog(QDialog):
    def __init__(self, materia, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Matéria")
        self.materia = materia
        
        self.nome_edit = QLineEdit(materia.nome)
        self.modulo_edit = QLineEdit(materia.modulo)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Em andamento", "Concluído", "Aguardando", "Reprovado", "Material de Uso"])
        self.status_combo.setCurrentText(materia.status)
        
        layout = QFormLayout()
        layout.addRow("Nome:", self.nome_edit)
        layout.addRow("Módulo:", self.modulo_edit)
        layout.addRow("Status:", self.status_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        self.setLayout(layout)
    
    def get_data(self):
        return {
            "nome": self.nome_edit.text(),
            "modulo": self.modulo_edit.text(),
            "status": self.status_combo.currentText()
        }

class DraggableListWidget(QListWidget):
    itemMoved = pyqtSignal(str, list)  # tipo, lista de itens

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.tipo = ""
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
    
    def dropEvent(self, event):
        super().dropEvent(event)
        self.emitir_movimento()
    
    def emitir_movimento(self):
        items = []
        for i in range(self.count()):
            item = self.item(i)
            items.append(item.text())
        self.itemMoved.emit(self.tipo, items)

class JanelaMateria(QMainWindow):
    def __init__(self, materia, parent=None):
        super().__init__(parent)
        self.materia = materia
        self.setWindowTitle(f"Matéria: {materia.nome}")
        self.setGeometry(200, 200, 800, 600)
        
         # Definir o ícone da janela
        if os.path.exists('icons/logo.png'):
            self.setWindowIcon(QIcon('icons/logo.png'))
        
        self.tabs = QTabWidget()
        
        # Books/Documents Tab
        self.tab_livros = QWidget()
        self.lista_livros = DraggableListWidget()
        self.lista_livros.tipo = "livro"
        self.botao_add_div_livro = QPushButton("Adicionar Divisão")
        self.botao_add_livro = QPushButton("Adicionar Arquivo")
        self.botao_remover_item_livro = QPushButton("Remover")
        
        layout_livros = QVBoxLayout()
        layout_livros.addWidget(self.lista_livros)
        
        botoes_livros = QHBoxLayout()
        botoes_livros.addWidget(self.botao_add_div_livro)
        botoes_livros.addWidget(self.botao_add_livro)
        botoes_livros.addWidget(self.botao_remover_item_livro)
        layout_livros.addLayout(botoes_livros)
        
        self.tab_livros.setLayout(layout_livros)
        
        # Videos Tab
        self.tab_videos = QWidget()
        self.lista_videos = DraggableListWidget()
        self.lista_videos.tipo = "video"
        self.botao_add_div_video = QPushButton("Adicionar Divisão")
        self.botao_add_video = QPushButton("Adicionar Vídeo")
        self.botao_remover_item_video = QPushButton("Remover")
        
        layout_videos = QVBoxLayout()
        layout_videos.addWidget(self.lista_videos)
        
        botoes_videos = QHBoxLayout()
        botoes_videos.addWidget(self.botao_add_div_video)
        botoes_videos.addWidget(self.botao_add_video)
        botoes_videos.addWidget(self.botao_remover_item_video)
        layout_videos.addLayout(botoes_videos)
        
        self.tab_videos.setLayout(layout_videos)
        
        # Live Classes Tab
        self.tab_aulas = QWidget()
        self.lista_aulas = DraggableListWidget()
        self.lista_aulas.tipo = "aula"
        self.botao_add_aula = QPushButton("Adicionar Aula")
        self.botao_remover_aula = QPushButton("Remover Aula")
        
        layout_aulas = QVBoxLayout()
        layout_aulas.addWidget(self.lista_aulas)
        
        botoes_aulas = QHBoxLayout()
        botoes_aulas.addWidget(self.botao_add_aula)
        botoes_aulas.addWidget(self.botao_remover_aula)
        layout_aulas.addLayout(botoes_aulas)
        
        self.tab_aulas.setLayout(layout_aulas)
        
        self.tabs.addTab(self.tab_livros, "Livros")
        self.tabs.addTab(self.tab_videos, "Vídeos")
        self.tabs.addTab(self.tab_aulas, "Aulas ao Vivo")
        
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        # Connections
        self.botao_add_div_livro.clicked.connect(lambda: self.adicionar_divisao('livro'))
        self.botao_add_livro.clicked.connect(lambda: self.adicionar_arquivo('livro'))
        self.botao_remover_item_livro.clicked.connect(lambda: self.remover_item('livro'))
        self.lista_livros.itemMoved.connect(self.atualizar_ordem_itens)
        self.lista_livros.itemDoubleClicked.connect(lambda: self.abrir_item('livro'))
        
        self.botao_add_div_video.clicked.connect(lambda: self.adicionar_divisao('video'))
        self.botao_add_video.clicked.connect(lambda: self.adicionar_arquivo('video'))
        self.botao_remover_item_video.clicked.connect(lambda: self.remover_item('video'))
        self.lista_videos.itemMoved.connect(self.atualizar_ordem_itens)
        self.lista_videos.itemDoubleClicked.connect(lambda: self.abrir_item('video'))
        
        self.botao_add_aula.clicked.connect(self.adicionar_aula)
        self.botao_remover_aula.clicked.connect(self.remover_aula)
        self.lista_aulas.itemMoved.connect(self.atualizar_ordem_itens)
        self.lista_aulas.itemDoubleClicked.connect(lambda: self.abrir_item('aula'))
        
        self.atualizar_listas()
    
    def abrir_item(self, tipo):
        lista = None
        if tipo == 'livro':
            lista = self.lista_livros
        elif tipo == 'video':
            lista = self.lista_videos
        else:
            lista = self.lista_aulas
        
        item = lista.currentItem()
        if item:
            texto = item.text()
            if "-------------------" not in texto:  # Não abre divisões
                caminho = texto.split(" | ")[1]
                
                # Verifica se é um link web
                if caminho.startswith(('http://', 'https://')):
                    webbrowser.open(caminho)
                else:
                    # Abre arquivo local
                    if sys.platform == 'win32':
                        os.startfile(caminho)
                    elif sys.platform == 'darwin':
                        os.system(f'open "{caminho}"')
                    else:
                        os.system(f'xdg-open "{caminho}"')
    
    def atualizar_ordem_itens(self, tipo, itens_texto):
        conteudos = []
        if tipo == 'livro':
            lista_original = self.materia.conteudos_livros
        elif tipo == 'video':
            lista_original = self.materia.conteudos_videos
        else:  # aula
            lista_original = self.materia.aulas_ao_vivo
        
        # Criar nova lista ordenada
        nova_ordem = []
        for texto in itens_texto:
            if "-------------------" in texto:
                nome = texto.split("---")[1].strip()
                conteudo = next((c for c in lista_original if c.nome == nome and getattr(c, 'is_divisao', False)), None)
            else:
                nome = texto.split(" | ")[0]
                conteudo = next((c for c in lista_original if c.nome == nome and not getattr(c, 'is_divisao', False)), None)
            
            if conteudo:
                nova_ordem.append(conteudo)
        
        # Atualizar no banco de dados
        self.materia.atualizar_ordem_conteudos(tipo, nova_ordem)
        self.atualizar_listas()
    
    def adicionar_divisao(self, tipo):
        nome, ok = QInputDialog.getText(self, "Nova Divisão", "Nome da divisão (opcional):")
        if ok:
            nome = nome if nome else "Div"
            self.materia.adicionar_divisao(tipo, nome)
            self.atualizar_listas()
    
    def adicionar_arquivo(self, tipo):
        if tipo == 'livro':
            filtros = "Documentos (*.pdf *.doc *.docx *.xls *.xlsx *.ppt *.pptx *.xml *.txt);;Todos os arquivos (*)"
        else:
            filtros = "Vídeos (*.mp4 *.avi *.mov *.mkv);;Todos os arquivos (*)"
        
        arquivos, _ = QFileDialog.getOpenFileNames(self, f"Selecionar Arquivo(s) de {tipo.capitalize()}", "", filtros)
        
        if arquivos:
            for arquivo in arquivos:
                nome = os.path.basename(arquivo)
                conteudo = Conteudo(nome, arquivo, tipo)
                try:
                    self.materia.adicionar_conteudo(conteudo)
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Não foi possível adicionar o arquivo: {e}")
            
            self.atualizar_listas()
    
    def adicionar_aula(self):
        link, ok = QInputDialog.getText(self, "Adicionar Aula ao Vivo", "Cole o link da aula (YouTube/Zoom):")
        if ok and link:
            nome = f"Aula {len(self.materia.aulas_ao_vivo) + 1}"
            conteudo = Conteudo(nome, link, 'aula')
            self.materia.adicionar_conteudo(conteudo)
            self.atualizar_listas()
    
    def remover_item(self, tipo):
        lista = self.lista_livros if tipo == 'livro' else self.lista_videos
        item = lista.currentItem()
        
        if item:
            resposta = QMessageBox.question(
                self, "Confirmar", "Tem certeza que deseja remover este item?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if resposta == QMessageBox.Yes:
                texto = item.text()
                if texto.startswith("-------------------") and texto.endswith("-------------------"):
                    nome = texto.replace("-", "").strip()
                    caminho = ""
                    is_divisao = True
                else:
                    partes = texto.split(" | ")
                    nome = partes[0]
                    caminho = partes[1] if len(partes) > 1 else ""
                    is_divisao = False
                
                conteudo = Conteudo(nome, caminho, tipo, is_divisao)
                self.materia.remover_conteudo(conteudo)
                self.atualizar_listas()
            
    def remover_aula(self):
        item = self.lista_aulas.currentItem()
        
        if item:
            resposta = QMessageBox.question(
                self, "Confirmar", "Tem certeza que deseja remover esta aula?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if resposta == QMessageBox.Yes:
                nome = item.text().split(" | ")[0]
                link = item.text().split(" | ")[1]
                conteudo = Conteudo(nome, link, 'aula')
                self.materia.remover_conteudo(conteudo)
                self.atualizar_listas()
    
    def atualizar_listas(self):
        self.lista_livros.clear()
        for conteudo in self.materia.conteudos_livros:
            item = QListWidgetItem(str(conteudo))
            if conteudo.is_divisao:
                item.setBackground(Qt.lightGray)
                font = QFont()
                font.setBold(True)
                item.setFont(font)
            self.lista_livros.addItem(item)
        
        self.lista_videos.clear()
        for conteudo in self.materia.conteudos_videos:
            item = QListWidgetItem(str(conteudo))
            if conteudo.is_divisao:
                item.setBackground(Qt.lightGray)
                font = QFont()
                font.setBold(True)
                item.setFont(font)
            self.lista_videos.addItem(item)
        
        self.lista_aulas.clear()
        for aula in self.materia.aulas_ao_vivo:
            self.lista_aulas.addItem(str(aula))

class JanelaConfig(QMainWindow):
    temaAlterado = pyqtSignal(bool)  # True para escuro, False para claro
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setGeometry(300, 300, 500, 400)
        
         # Definir o ícone da janela
        if os.path.exists('icons/logo.png'):
            self.setWindowIcon(QIcon('icons/logo.png'))
        
        self.tabs = QTabWidget()
        
        tab_config = QWidget()
        self.botao_tema = QPushButton("Mudar Tema (Claro/Escuro)")
        self.botao_backup = QPushButton("Exportar Backup (JSON)")
        
        layout_config = QVBoxLayout()
        layout_config.addWidget(self.botao_tema)
        layout_config.addWidget(self.botao_backup)
        tab_config.setLayout(layout_config)
        
        tab_ajuda = QWidget()
        texto_ajuda = QTextBrowser()
        texto_ajuda.setPlainText(
            "=== AJUDA ===\n\n"
            "1. Adicionar Matéria:\n"
            "   - Clique em 'Adicionar Matéria' e preencha os dados\n\n"
            "2. Editar/Remover Matéria:\n"
            "   - Selecione uma matéria e clique nos botões correspondentes\n\n"
            "3. Adicionar Conteúdo:\n"
            "   - Na aba da matéria, use os botões para adicionar:\n"
            "     * Livros/Documentos (PDF, Word, Excel, etc.)\n"
            "     * Vídeos (MP4, AVI, etc.)\n"
            "     * Aulas ao vivo (links)\n\n"
            "4. Divisões:\n"
            "   - Adicione divisões para organizar seus materiais\n\n"
            "5. Pesquisar:\n"
            "   - Digite na barra de pesquisa para filtrar matérias"
        )
        
        layout_ajuda = QVBoxLayout()
        layout_ajuda.addWidget(texto_ajuda)
        tab_ajuda.setLayout(layout_ajuda)
        
        self.tabs.addTab(tab_config, "Configurações")
        self.tabs.addTab(tab_ajuda, "Ajuda")
        
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        self.botao_tema.clicked.connect(self.mudar_tema)
        self.botao_backup.clicked.connect(self.exportar_backup)
        
        self.tema_escuro = True  # Tema escuro por padrão
    
    def mudar_tema(self):
        self.tema_escuro = not self.tema_escuro
        self.temaAlterado.emit(self.tema_escuro)
        self.aplicar_tema()
    
    def aplicar_tema(self):
        estilo_comum = """
            QMainWindow, QDialog {
                font-size: 14px;
            }
            QPushButton {
                padding: 10px 15px;
                min-height: 40px;
                min-width: 120px;
            }
            QLineEdit {
                padding: 8px;
                min-height: 30px;
            }
            QListWidget {
                font-size: 14px;
            }
            QListWidget::item {
                padding: 6px;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                padding: 5px;
            }
            QTabBar::tab {
                padding: 8px 12px;
            }
        """
        
        if self.tema_escuro:
            self.setStyleSheet(estilo_comum + """
                QMainWindow, QDialog {
                    background-color: #333;
                    color: white;
                }
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #777;
                }
                QListWidget {
                    background-color: #444;
                    color: white;
                }
                QLineEdit {
                    background-color: #444;
                    color: white;
                    border: 1px solid #555;
                }
                QTabWidget::pane {
                    border: 1px solid #444;
                    background: #333;
                }
                QTabBar::tab {
                    background: #555;
                    color: white;
                    border: 1px solid #444;
                }
                QTabBar::tab:selected {
                    background: #777;
                }
            """)
        else:
            self.setStyleSheet(estilo_comum + """
                QMainWindow, QDialog {
                    background-color: #f0f0f0;
                    color: black;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                }
                QListWidget {
                    background-color: white;
                    color: black;
                }
                QLineEdit {
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                }
                QTabWidget::pane {
                    border: 1px solid #ccc;
                    background: #f0f0f0;
                }
                QTabBar::tab {
                    background: #ddd;
                    color: black;
                    border: 1px solid #ccc;
                }
                QTabBar::tab:selected {
                    background: #f0f0f0;
                }
            """)
    
    def exportar_backup(self):
        caminho = QFileDialog.getSaveFileName(
            self, "Exportar Backup", "", "JSON Files (*.json)"
        )[0]
        
        if caminho:
            materias = Materia.carregar_todas()
            dados = []
            
            for materia in materias:
                dados.append({
                    "nome": materia.nome,
                    "modulo": materia.modulo,
                    "status": materia.status,
                    "conteudos_livros": [{"nome": c.nome, "caminho": c.caminho, "is_divisao": c.is_divisao} 
                                      for c in materia.conteudos_livros],
                    "conteudos_videos": [{"nome": c.nome, "caminho": c.caminho, "is_divisao": c.is_divisao} 
                                       for c in materia.conteudos_videos],
                    "aulas_ao_vivo": [{"nome": a.nome, "caminho": a.caminho} for a in materia.aulas_ao_vivo]
                })
            
            with open(caminho, 'w') as f:
                json.dump(dados, f, indent=4)
            
            QMessageBox.information(self, "Sucesso", "Backup exportado com sucesso!")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App de Matérias")
        self.setGeometry(100, 100, 800, 600)
        
         # Definir o ícone da janela
        if os.path.exists('icons/logo.png'):
            self.setWindowIcon(QIcon('icons/logo.png'))
        
        # Variável para controlar o tema
        self.tema_escuro = True  # Tema escuro por padrão
        
        self.materias = Materia.carregar_todas()
        
        self.lista_materias = QListWidget()
        self.lista_materias.setIconSize(QSize(32, 32))
        self.botao_add_materia = QPushButton("Adicionar Matéria")
        self.botao_editar_materia = QPushButton("Editar Matéria")
        self.botao_remover_materia = QPushButton("Remover Matéria")
        self.botao_config = QPushButton("Configurações")
        self.barra_pesquisa = QLineEdit()
        self.barra_pesquisa.setPlaceholderText("Pesquisar matéria...")
        
        layout = QVBoxLayout()
        layout.addWidget(self.barra_pesquisa)
        layout.addWidget(self.lista_materias)
        
        botoes_layout = QHBoxLayout()
        botoes_layout.addWidget(self.botao_add_materia)
        botoes_layout.addWidget(self.botao_editar_materia)
        botoes_layout.addWidget(self.botao_remover_materia)
        layout.addLayout(botoes_layout)
        
        layout.addWidget(self.botao_config)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        self.botao_add_materia.clicked.connect(self.adicionar_materia)
        self.botao_editar_materia.clicked.connect(self.editar_materia)
        self.botao_remover_materia.clicked.connect(self.remover_materia)
        self.botao_config.clicked.connect(self.abrir_config)
        self.lista_materias.itemDoubleClicked.connect(self.abrir_materia)
        self.barra_pesquisa.textChanged.connect(self.filtrar_materias)
        
        self.aplicar_tema()
        self.atualizar_lista_materias()
    
    def aplicar_tema(self):
        estilo_comum = """
            QMainWindow {
                font-size: 14px;
            }
            QPushButton {
                padding: 10px 15px;
                min-height: 40px;
                min-width: 120px;
            }
            QLineEdit {
                padding: 8px;
                min-height: 30px;
            }
            QListWidget {
                font-size: 14px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """
        
        if self.tema_escuro:
            self.setStyleSheet(estilo_comum + """
                QMainWindow {
                    background-color: #333;
                    color: white;
                }
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #777;
                }
                QListWidget {
                    background-color: #444;
                    color: white;
                }
                QLineEdit {
                    background-color: #444;
                    color: white;
                    border: 1px solid #555;
                }
            """)
        else:
            self.setStyleSheet(estilo_comum + """
                QMainWindow {
                    background-color: #f0f0f0;
                    color: black;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                }
                QListWidget {
                    background-color: white;
                    color: black;
                }
                QLineEdit {
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                }
            """)
    
    def mudar_tema(self, escuro):
        self.tema_escuro = escuro
        self.aplicar_tema()
    
    def adicionar_materia(self):
        nome, ok = QInputDialog.getText(self, "Nova Matéria", "Nome da Matéria:")
        if ok and nome:
            modulo, ok = QInputDialog.getText(self, "Módulo", "Módulo da Matéria:")
            if ok and modulo:
                status, ok = QInputDialog.getItem(
                    self, "Status", "Selecione o status:",
                    ["Em andamento", "Concluído", "Aguardando", "Reprovado", "Material de Uso"], 0, False
                )
                if ok:
                    nova_materia = Materia(nome=nome, modulo=modulo, status=status)
                    nova_materia.salvar()
                    self.materias = Materia.carregar_todas()
                    self.atualizar_lista_materias()
    
    def editar_materia(self):
        item = self.lista_materias.currentItem()
        if item:
            materia_id = item.data(Qt.UserRole)
            materia = next((m for m in self.materias if m.id == materia_id), None)
            if materia:
                dialog = EditarMateriaDialog(materia)
                if dialog.exec_():
                    data = dialog.get_data()
                    materia.nome = data["nome"]
                    materia.modulo = data["modulo"]
                    materia.status = data["status"]
                    materia.salvar()
                    self.atualizar_lista_materias()
    
    def remover_materia(self):
        item = self.lista_materias.currentItem()
        if item:
            materia_id = item.data(Qt.UserRole)
            materia = next((m for m in self.materias if m.id == materia_id), None)
            if materia:
                resposta = QMessageBox.question(
                    self, "Confirmar", f"Tem certeza que deseja remover '{materia.nome}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resposta == QMessageBox.Yes:
                    Materia.remover_por_id(materia.id)
                    self.materias = Materia.carregar_todas()
                    self.atualizar_lista_materias()
    
    def abrir_materia(self, item):
        materia_id = item.data(Qt.UserRole)
        materia = next((m for m in self.materias if m.id == materia_id), None)
        if materia:
            self.janela_materia = JanelaMateria(materia, self)
            self.janela_materia.show()
    
    def abrir_config(self):
        self.janela_config = JanelaConfig(self)
        self.janela_config.temaAlterado.connect(self.mudar_tema)
        self.janela_config.show()
    
    def filtrar_materias(self):
        texto = self.barra_pesquisa.text().lower()
        for i in range(self.lista_materias.count()):
            item = self.lista_materias.item(i)
            materia_id = item.data(Qt.UserRole)
            materia = next((m for m in self.materias if m.id == materia_id), None)
            if materia and texto.lower() in materia.nome.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def atualizar_lista_materias(self):
        self.lista_materias.clear()
        for materia in self.materias:
            item = QListWidgetItem(str(materia))
            item.setData(Qt.UserRole, materia.id)
            item.setIcon(QIcon("icons/book.png"))
            self.lista_materias.addItem(item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if not os.path.exists("icons"):
        os.makedirs("icons")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())