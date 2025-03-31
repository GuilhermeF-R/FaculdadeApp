class Conteudo:
    def __init__(self, nome, caminho):
        self.nome = nome
        self.caminho = caminho  # Pode ser um arquivo ou link

    def __str__(self):
        return f"{self.nome} | {self.caminho}"