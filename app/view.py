from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QFileDialog, QPushButton, QLabel, QWidget, QMessageBox, QComboBox
from app.service import fetch_neighborhoods, generate_gpx

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_neighborhoods()

    def init_ui(self):
        self.setWindowTitle("GPX BH")
        self.setGeometry(200, 200, 400, 300)

        icon_path = "assets/icon.ico"
        self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()

        self.label = QLabel("Carregando bairros...")
        self.combo_neighborhoods = QComboBox()
        self.generate_gpx_button = QPushButton("Gerar GPX")
        self.load_neighborhoods_button = QPushButton("Carregar Bairros")

        layout.addWidget(self.label)
        layout.addWidget(self.load_neighborhoods_button)
        layout.addWidget(self.combo_neighborhoods)
        layout.addWidget(self.generate_gpx_button)

        self.generate_gpx_button.clicked.connect(self.generate_gpx)
        self.load_neighborhoods_button.clicked.connect(self.load_neighborhoods)

        self.setLayout(layout)

    def load_neighborhoods(self):
        self.label.setText("Carregando bairros...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.repaint()

        try:
            neighborhoods = fetch_neighborhoods()
            if neighborhoods:
                self.combo_neighborhoods.clear()
                self.combo_neighborhoods.setEditable(True)
                self.combo_neighborhoods.addItems(neighborhoods.keys())
                self.neighborhoods_data = neighborhoods
                self.label.setText("Escolha um bairro e clique em Gerar GPX")
                self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.label.setStyleSheet("""
                    font-size: 16px; 
                    font-weight: bold; 
                    text-align: center;
                    margin: 10px 0;
                """)
            else:
                self.label.setText("Nenhum bairro encontrado.")
        except RuntimeError as e:
            QMessageBox.critical(self, "Erro", str(e))
            self.label.setText("Falha ao carregar os bairros.")
        finally:
            self.label.repaint()

    def generate_gpx(self):
        selected_neighborhood = self.combo_neighborhoods.currentText()
        if not selected_neighborhood:
            QMessageBox.warning(self, "Atenção", "Por favor, selecione um bairro.")
            return

        coordinates = self.neighborhoods_data.get(selected_neighborhood)
        if not coordinates:
            QMessageBox.critical(self, "Erro", "Coordenadas não encontradas para o bairro selecionado.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo GPX", f"{selected_neighborhood.replace(' ', '_')}.gpx", "Arquivos GPX (*.gpx)")

        if file_path:
            try:
                result = generate_gpx(selected_neighborhood, coordinates, file_path)
                QMessageBox.information(self, "Sucesso", f"Arquivo GPX salvo com sucesso em {file_path}.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao salvar o arquivo GPX: {e}")
        else:
            QMessageBox.information(self, "Informação", "Operação de salvamento foi cancelada.")
