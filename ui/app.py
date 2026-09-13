import customtkinter as ctk
from credito_app.database.connection import get_connection
from credito_app.database.schema import inicializar_base_datos
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.services.reporte_service import ReporteService
from credito_app.services.pdf_service import PDFService
from credito_app.ui.theme import COLORS
from credito_app.ui.components.sidebar import Sidebar
from credito_app.ui.components.notifications import NotificationBar

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        self.title("CrediNoda - Sistema de Gestión de Créditos")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        
        inicializar_base_datos()
        self.conn = get_connection()
        
        self.cliente_service = ClienteService(self.conn)
        self.credito_service = CreditoService(self.conn)
        self.pago_service = PagoService(self.conn)
        self.reporte_service = ReporteService(self.conn)
        self.pdf_service = PDFService()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.sidebar = Sidebar(self, on_navigate=self.navigate)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.notification_bar = NotificationBar(self.content_frame)
        self.notification_bar.grid(row=0, column=0, sticky="ew")
        
        self.view_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.view_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        
        self.current_view = None
        self.navigate("dashboard")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def navigate(self, view_name: str, **kwargs):
        if self.current_view:
            self.current_view.destroy()
            
        if view_name == "dashboard":
            from credito_app.ui.views.dashboard_view import DashboardView
            self.current_view = DashboardView(self.view_container, self)
        elif view_name == "clientes":
            from credito_app.ui.views.clientes_view import ClientesView
            self.current_view = ClientesView(self.view_container, self)
        elif view_name == "cliente_detail":
            from credito_app.ui.views.cliente_detail_view import ClienteDetailView
            self.current_view = ClienteDetailView(self.view_container, self, **kwargs)
        elif view_name == "credito_new":
            from credito_app.ui.views.credito_view import CreditoView
            self.current_view = CreditoView(self.view_container, self, **kwargs)
        elif view_name == "credito_detail":
            from credito_app.ui.views.credito_detail_view import CreditoDetailView
            self.current_view = CreditoDetailView(self.view_container, self, **kwargs)
        elif view_name == "pagos":
            from credito_app.ui.views.pagos_view import PagosView
            self.current_view = PagosView(self.view_container, self)
        elif view_name == "reportes":
            from credito_app.ui.views.reportes_view import ReportesView
            self.current_view = ReportesView(self.view_container, self)
            
        if self.current_view:
            self.current_view.pack(fill="both", expand=True)
            
        self.sidebar.set_active(view_name)
        
    def show_notification(self, message: str, type: str = "success"):
        if type == "success":
            self.notification_bar.show_success(message)
        elif type == "error":
            self.notification_bar.show_error(message)
        elif type == "warning":
            self.notification_bar.show_warning(message)

    def generar_comprobante_pago(
        self,
        pago_id: int,
        preguntar_destino: bool = False,
        abrir_al_terminar: bool = True
    ):
        """
        Genera el comprobante en PDF para el pago indicado.
        Si preguntar_destino es True, solicita la ubicación al usuario.
        Si abrir_al_terminar es True, abre el archivo generado en el visor del sistema.
        """
        try:
            datos = self.pago_service.obtener_datos_comprobante(pago_id)
            ruta_destino = None

            if preguntar_destino:
                from tkinter import filedialog
                cliente_slug = self.pdf_service._sanitizar_nombre_archivo(datos.get("cliente_nombre", "Cliente"))
                num_recibo = datos.get("numero_recibo", f"REC-{pago_id:05d}")
                fecha_pago = datos["fecha_pago"]
                fecha_str = fecha_pago.strftime("%Y%m%d") if hasattr(fecha_pago, "strftime") else str(fecha_pago)
                nombre_defecto = f"Recibo_{num_recibo}_{cliente_slug}_{fecha_str}.pdf"

                ruta_guardar = filedialog.asksaveasfilename(
                    parent=self,
                    title="Guardar Comprobante de Pago",
                    defaultextension=".pdf",
                    filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
                    initialfile=nombre_defecto,
                    initialdir=str(self.pdf_service.output_dir)
                )
                if not ruta_guardar:
                    return None
                ruta_destino = ruta_guardar

            pdf_path = self.pdf_service.generar_comprobante_pago(datos, output_path=ruta_destino)

            if abrir_al_terminar:
                self.pdf_service.abrir_documento(pdf_path)

            self.show_notification(f"Comprobante generado: {pdf_path.name}", "success")
            return str(pdf_path)

        except Exception as e:
            self.show_notification(f"Error al generar comprobante: {str(e)}", "error")
            return None

            
    def on_closing(self):
        if self.conn:
            self.conn.close()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
