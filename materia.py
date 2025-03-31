from datetime import datetime

class Materia:
    def __init__(self, nome, modulo, status="Em andamento"):
        self.nome = nome
        self.modulo = modulo
        self.status = status
        self.data_registro = datetime.now()
        self.livros = []      # Lista de arquivos PDF/Imagens
        self.videos = []      # Lista de arquivos MP4
        self.aulas_ao_vivo = []  # Lista de links (YouTube, Zoom, etc.)

    def __str__(self):
        return f"{self.nome} ({self.modulo}) - {self.status}"