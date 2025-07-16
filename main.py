import os
import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidget,
                             QPushButton, QTabWidget, QFileDialog, QMessageBox, QInputDialog,
                             QListWidgetItem)
from PyQt5.QtCore import Qt
from PIL import Image
import shutil
from functools import partial

class Optimizer:
    @staticmethod
    def get_image_format(file_path):
        """Determina o formato da imagem sem usar imghdr (que está obsoleto)"""
        try:
            with Image.open(file_path) as img:
                return img.format
        except:
            return None

    @staticmethod
    def optimize_image(input_path, output_folder, quality=85, max_size=(1920, 1080)):
        """Reduz tamanho de imagens mantendo qualidade visual"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
        
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_folder, f"opt_{filename}")
        
        try:
            with Image.open(input_path) as img:
                # Redimensiona se for muito grande
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.LANCZOS)
                
                # Determina o formato
                img_format = Optimizer.get_image_format(input_path) or 'JPEG'
                
                # Configurações de qualidade por formato
                save_kwargs = {'optimize': True}
                if img_format.upper() in ['JPEG', 'JPG']:
                    save_kwargs['quality'] = quality
                    save_kwargs['progressive'] = True
                elif img_format.upper() == 'PNG':
                    save_kwargs['compress_level'] = 6
                
                img.save(output_path, **save_kwargs)
            
            return output_path
        except Exception as e:
            print(f"Erro ao otimizar imagem: {e}")
            return input_path

    @staticmethod
    def optimize_generic_file(input_path, output_folder):
        """Copia arquivos não-otimizáveis mantendo a organização"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
        
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_folder, f"org_{filename}")
        
        try:
            shutil.copy2(input_path, output_path)
            return output_path
        except Exception as e:
            print(f"Erro ao organizar arquivo: {e}")
            return input_path

class MaterialApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Materiais Escolares Leve")
        self.setGeometry(100, 100, 800, 600)
        
        self.optimized_folder = "optimized_media"
        os.makedirs(self.optimized_folder, exist_ok=True)
        
        self.init_db()
        self.init_ui()
    
    def init_db(self):
        self.conn = sqlite3.connect('materiais_leve.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            modulo TEXT,
            status TEXT
        )''')
        
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS arquivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER,
            nome TEXT,
            caminho_original TEXT,
            caminho_otimizado TEXT,
            tipo TEXT,
            tamanho_original REAL,
            tamanho_otimizado REAL,
            FOREIGN KEY (materia_id) REFERENCES materias(id)
        )''')
        
        self.conn.commit()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # Tab de documentos
        self.doc_tab = QWidget()
        self.doc_list = QListWidget()
        self.btn_add_doc = QPushButton("Adicionar Documento")
        self.btn_open_doc = QPushButton("Abrir Documento")
        
        doc_layout = QVBoxLayout()
        doc_layout.addWidget(self.doc_list)
        doc_layout.addWidget(self.btn_add_doc)
        doc_layout.addWidget(self.btn_open_doc)
        self.doc_tab.setLayout(doc_layout)
        
        # Tab de imagens
        self.image_tab = QWidget()
        self.image_list = QListWidget()
        self.btn_add_image = QPushButton("Adicionar Imagem")
        self.btn_view_image = QPushButton("Visualizar Imagem")
        
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.image_list)
        image_layout.addWidget(self.btn_add_image)
        image_layout.addWidget(self.btn_view_image)
        self.image_tab.setLayout(image_layout)
        
        self.tabs.addTab(self.doc_tab, "Documentos")
        self.tabs.addTab(self.image_tab, "Imagens")
        layout.addWidget(self.tabs)
        
        self.btn_optimize_all = QPushButton("Otimizar Todos os Arquivos")
        layout.addWidget(self.btn_optimize_all)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        self.btn_add_doc.clicked.connect(partial(self.add_file, 'documento'))
        self.btn_open_doc.clicked.connect(self.open_file)
        self.btn_add_image.clicked.connect(partial(self.add_file, 'imagem'))
        self.btn_view_image.clicked.connect(self.view_image)
        self.btn_optimize_all.clicked.connect(self.optimize_all)
        
        self.load_files()
    
    def add_file(self, file_type):
        if file_type == 'imagem':
            file_filter = "Imagens (*.jpg *.jpeg *.png *.bmp *.gif);;Todos os arquivos (*)"
        else:
            file_filter = "Documentos (*.pdf *.doc *.docx *.xls *.xlsx *.ppt *.pptx *.txt);;Todos os arquivos (*)"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Selecionar {file_type.capitalize()}", "", file_filter)
        
        if file_path:
            nome = os.path.basename(file_path)
            tamanho = os.path.getsize(file_path) / (1024 * 1024)  # MB
            
            self.cursor.execute(
                'INSERT INTO arquivos (nome, caminho_original, tipo, tamanho_original) VALUES (?, ?, ?, ?)',
                (nome, file_path, file_type, tamanho)
            )
            self.conn.commit()
            self.optimize_file(self.cursor.lastrowid)
            self.load_files()
    
    def optimize_file(self, file_id):
        self.cursor.execute('SELECT * FROM arquivos WHERE id=?', (file_id,))
        file_data = self.cursor.fetchone()
        
        if not file_data:
            return
        
        id, _, nome, original_path, opt_path, tipo, size_orig, size_opt = file_data
        
        try:
            if tipo == 'imagem':
                optimized_path = Optimizer.optimize_image(original_path, self.optimized_folder)
            else:
                optimized_path = Optimizer.optimize_generic_file(original_path, self.optimized_folder)
            
            opt_size = os.path.getsize(optimized_path) / (1024 * 1024)
            self.cursor.execute(
                'UPDATE arquivos SET caminho_otimizado=?, tamanho_otimizado=? WHERE id=?',
                (optimized_path, opt_size, id)
            )
            self.conn.commit()
            
        except Exception as e:
            print(f"Erro ao processar arquivo {id}: {e}")
    
    def optimize_all(self):
        self.cursor.execute('SELECT id FROM arquivos WHERE caminho_otimizado IS NULL')
        files_to_optimize = self.cursor.fetchall()
        
        for (file_id,) in files_to_optimize:
            self.optimize_file(file_id)
        
        self.load_files()
        QMessageBox.information(self, "Concluído", "Todos os arquivos foram processados!")
    
    def open_file(self):
        selected = self.doc_list.currentItem()
        if selected:
            file_id = selected.data(Qt.UserRole)
            self.cursor.execute('SELECT caminho_otimizado, caminho_original FROM arquivos WHERE id=?', (file_id,))
            result = self.cursor.fetchone()
            if result:
                opt_path, orig_path = result
                path_to_open = opt_path if opt_path else orig_path
                try:
                    os.startfile(path_to_open)
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Não foi possível abrir o arquivo: {e}")
    
    def view_image(self):
        selected = self.image_list.currentItem()
        if selected:
            file_id = selected.data(Qt.UserRole)
            self.cursor.execute('SELECT caminho_otimizado, caminho_original FROM arquivos WHERE id=?', (file_id,))
            result = self.cursor.fetchone()
            if result:
                opt_path, orig_path = result
                path_to_view = opt_path if opt_path else orig_path
                try:
                    os.startfile(path_to_view)
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Não foi possível abrir a imagem: {e}")
    
    def load_files(self):
        self.doc_list.clear()
        self.image_list.clear()
        
        # Carrega documentos
        self.cursor.execute('SELECT id, nome, tamanho_original, tamanho_otimizado FROM arquivos WHERE tipo="documento"')
        for id, nome, size_orig, size_opt in self.cursor.fetchall():
            item_text = f"{nome} - Original: {size_orig:.1f}MB"
            if size_opt:
                reduction = (size_orig - size_opt) / size_orig * 100
                item_text += f" | Organizado: {size_opt:.1f}MB ({reduction:.0f}% diferente)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, id)
            self.doc_list.addItem(item)
        
        # Carrega imagens
        self.cursor.execute('SELECT id, nome, tamanho_original, tamanho_otimizado FROM arquivos WHERE tipo="imagem"')
        for id, nome, size_orig, size_opt in self.cursor.fetchall():
            item_text = f"{nome} - Original: {size_orig:.1f}MB"
            if size_opt:
                reduction = (size_orig - size_opt) / size_orig * 100
                item_text += f" | Otimizado: {size_opt:.1f}MB ({reduction:.0f}% menor)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, id)
            self.image_list.addItem(item)
    
    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Verifica se o Pillow está instalado
    try:
        from PIL import Image
    except ImportError:
        QMessageBox.critical(None, "Erro", 
            "Pillow não está instalado. Instale com: pip install pillow")
        sys.exit(1)
    
    window = MaterialApp()
    window.show()
    sys.exit(app.exec_())