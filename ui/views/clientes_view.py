import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.tables import DataTable
from credito_app.ui.components.dialogs import ClienteDialog
from credito_app.ui.utils.formatters import formato_fecha
from credito_app.modules.excepciones import CrediNodaError

class ClientesView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        self.last_data_version = getattr(self.app, "data_version", 1)
        self._build_ui()
        self._load_data()
        
    def on_show(self, force: bool = False):
        """Se invoca al mostrar la vista en pantalla. Recarga clientes si los datos cambiaron."""
        app_version = getattr(self.app, "data_version", 1)
        if force or self.last_data_version < app_version:
            self.refresh()
            self.last_data_version = app_version

    def _build_ui(self):
        self.header = SectionHeader(
            self, 
            title="Clientes", 
            button_text="+ Nuevo Cliente", 
            button_command=self.open_cliente_dialog
        )
        self.header.pack(fill="x", pady=(0, 20))
        
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(fill="x", pady=(0, 15))
        
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Buscar por nombre o documento...", width=300)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.search())
        
        self.search_btn = ctk.CTkButton(self.search_frame, text="Buscar", width=100, command=self.search)
        self.search_btn.pack(side="left")
        
        columns = [
            {"key": "nombre", "text": "Nombre", "width": 220, "weight": 2, "anchor": "w"},
            {"key": "documento", "text": "Documento", "width": 160, "weight": 1, "anchor": "w"},
            {"key": "telefono", "text": "Teléfono", "width": 150, "weight": 1, "anchor": "w"},
            {"key": "creditos", "text": "Créditos", "width": 100, "weight": 0, "anchor": "center"},
            {"key": "fecha", "text": "Registro", "width": 120, "weight": 0, "anchor": "center"}
        ]
        
        self.table = DataTable(self, columns=columns, on_row_click=self.on_row_click)
        self.table.pack(fill="both", expand=True)
        
    def search(self):
        term = self.search_entry.get().strip()
        self._load_data(term)
        
    def _load_data(self, search_term=""):
        try:
            clientes = self.app.cliente_service.buscar_clientes(search_term)
            rows = []
            for c in clientes:
                creditos = self.app.cliente_service.obtener_creditos_cliente(c.id)
                rows.append({
                    "id": c.id,
                    "nombre": c.nombre,
                    "documento": c.documento,
                    "telefono": c.telefono or "",
                    "creditos": str(len(creditos)),
                    "fecha": formato_fecha(c.fecha_registro) if c.fecha_registro else ""
                })
            self.table.set_data(rows)
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")
        except Exception:
            self.app.show_notification("Ocurrió un error inesperado.", "error")
            
    def _on_cliente_guardado(self):
        if hasattr(self.app, "notificar_cambio_datos"):
            self.app.notificar_cambio_datos()
        self.refresh()

    def open_cliente_dialog(self):
        dialog = ClienteDialog(self, self.app.cliente_service, on_save=self._on_cliente_guardado)
        
    def on_row_click(self, row_data):
        if "id" in row_data:
            self.app.navigate("cliente_detail", cliente_id=row_data["id"])
            
    def refresh(self):
        self._load_data(self.search_entry.get().strip())
