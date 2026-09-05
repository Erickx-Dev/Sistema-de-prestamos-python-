from decimal import Decimal
from credito_app.database.connection import get_connection
from credito_app.database.schema import inicializar_base_datos
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.modules.credito import FrecuenciaPago

def main():
    db_path = None  # Uses default from config (data/creditos.db)
    
    # 1. Initialize database
    inicializar_base_datos(db_path)
    conn = get_connection(db_path)
    
    cliente_svc = ClienteService(conn)
    credito_svc = CreditoService(conn)
    pago_svc = PagoService(conn)
    
    try:
        # 2. Create a client
        cliente = cliente_svc.crear_cliente("Juan Pérez", "3001234567", "CC-123456")
        print(f"Cliente creado: {cliente.nombre} (Doc: {cliente.documento})")
        
        # 3. Create a credit
        capital = Decimal("1000000")
        plazo_meses = 3
        credito = credito_svc.crear_credito(cliente.id, capital, plazo_meses, FrecuenciaPago.SEMANAL)
        
        # 4. Print credit details
        print(f"\n--- Detalles del Crédito ---")
        print(f"Capital: ${credito.capital:,.2f}")
        print(f"Intereses: ${credito.total_intereses:,.2f}")
        print(f"Total a pagar: ${credito.total_pagar:,.2f}")
        print(f"Estado: {credito.estado.value}")
        
        # 5. Print payment plan
        print(f"\n--- Plan de Pagos ---")
        plan = credito_svc.obtener_plan_pagos(credito.id)
        for cuota in plan:
            print(f"Cuota {cuota.numero_cuota}: Vence {cuota.fecha_vencimiento}, Monto ${cuota.monto:,.2f}, Estado: {cuota.estado.value}")
            
        # 6. Register 2 payments
        print(f"\n--- Registrando pagos ---")
        # Full payment for cuota 1
        pago_1 = pago_svc.registrar_pago(credito.id, plan[0].id, plan[0].monto)
        print(f"Pago registrado por cuota 1: ${pago_1.monto:,.2f}")
        
        # Partial payment for cuota 2
        monto_parcial = Decimal("50000")
        pago_2 = pago_svc.registrar_pago(credito.id, plan[1].id, monto_parcial)
        print(f"Pago parcial registrado por cuota 2: ${pago_2.monto:,.2f}")
        
        # 7. Print balance
        saldo = credito_svc.calcular_saldo_pendiente(credito.id)
        print(f"\nSaldo pendiente del crédito: ${saldo:,.2f}")
        
        # 8. Print payment history
        print(f"\n--- Historial de Pagos ---")
        pagos = pago_svc.obtener_historial_pagos(credito.id)
        for pago in pagos:
            print(f"Pago de ${pago.monto:,.2f} el {pago.fecha_pago}")
            
        # 9. Print credit status
        estado = credito_svc.determinar_estado_credito(credito.id)
        print(f"\nEstado actual del crédito: {estado.value}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
