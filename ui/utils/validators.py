import re
from decimal import Decimal, InvalidOperation

def parsear_monto(texto: str) -> Decimal:
    """Convierte texto a Decimal, admitiendo formatos flexibles:
    - 11333.33 o 11333,33 (decimales con punto o coma)
    - 11.333,33 o 11,333.33 (separadores de miles y decimales)
    - 11333 (enteros sin separadores)
    - 1.000.000 o 1,000,000 (separadores de miles)
    - $11.333,33 o $ 11333.33 (con signo de pesos y espacios)
    """
    if texto is None:
        raise InvalidOperation("El texto es None")
    
    texto = str(texto).strip().replace("$", "").replace(" ", "").replace("\u00a0", "")
    if not texto:
        raise InvalidOperation("Texto vacío")
    
    sign = ""
    if texto.startswith("-"):
        sign = "-"
        texto = texto[1:]
    elif texto.startswith("+"):
        texto = texto[1:]
        
    if not texto:
        raise InvalidOperation("No contiene dígitos")
        
    if not re.match(r"^[\d.,]+$", texto):
        raise InvalidOperation(f"Caracteres inválidos en monto: {texto}")

    if ".." in texto or ",," in texto or ".," in texto or ",." in texto:
        raise InvalidOperation("Separadores consecutivos no permitidos")
        
    dots = texto.count(".")
    commas = texto.count(",")
    
    # Caso 1: Hay tanto puntos como comas (ej. 1.000,50 o 1,000.50)
    if dots > 0 and commas > 0:
        last_dot = texto.rfind(".")
        last_comma = texto.rfind(",")
        if last_comma > last_dot:
            # Coma es el separador decimal (ej. 1.000.000,50 o 11.333,33)
            if commas > 1:
                raise InvalidOperation("Múltiples separadores decimales")
            thousand_parts = texto[:last_comma].split(".")
            if len(thousand_parts) > 1:
                for grp in thousand_parts[1:]:
                    if len(grp) != 3:
                        raise InvalidOperation("Grupos de miles inválidos")
            texto_limpio = texto.replace(".", "").replace(",", ".")
        else:
            # Punto es el separador decimal (ej. 1,000,000.50 o 11,333.33)
            if dots > 1:
                raise InvalidOperation("Múltiples separadores decimales")
            thousand_parts = texto[:last_dot].split(",")
            if len(thousand_parts) > 1:
                for grp in thousand_parts[1:]:
                    if len(grp) != 3:
                        raise InvalidOperation("Grupos de miles inválidos")
            texto_limpio = texto.replace(",", "")
            
    # Caso 2: Solo hay puntos (ej. 11333.33, 1.000.000, 10.000, 500.50, 11.333.33)
    elif dots > 0:
        parts = texto.split(".")
        if len(parts[-1]) in (1, 2):
            # El último punto es decimal; cualquier punto anterior era de miles
            if len(parts) > 2:
                for grp in parts[1:-1]:
                    if len(grp) != 3:
                        raise InvalidOperation("Grupos de miles inválidos")
            entero = "".join(parts[:-1])
            decimal = parts[-1]
            texto_limpio = f"{entero if entero else '0'}.{decimal}"
        elif len(parts) > 1:
            if len(parts) == 2 and len(parts[0]) > 3:
                texto_limpio = f"{parts[0]}.{parts[1]}"
            else:
                for grp in parts[1:]:
                    if len(grp) != 3:
                        raise InvalidOperation("Grupos de miles inválidos")
                texto_limpio = "".join(parts)
        else:
            texto_limpio = texto

    # Caso 3: Solo hay comas (ej. 11333,33, 1,000,000, 10,000, 500,50, 11,333,33)
    elif commas > 0:
        parts = texto.split(",")
        if len(parts[-1]) in (1, 2):
            if len(parts) > 2:
                for grp in parts[1:-1]:
                    if len(grp) != 3:
                        raise InvalidOperation("Grupos de miles inválidos")
            entero = "".join(parts[:-1])
            decimal = parts[-1]
            texto_limpio = f"{entero if entero else '0'}.{decimal}"
        elif len(parts) > 1:
            if len(parts) == 2 and len(parts[0]) > 3:
                texto_limpio = f"{parts[0]}.{parts[1]}"
            else:
                for grp in parts[1:]:
                    if len(grp) != 3:
                        raise InvalidOperation("Grupos de miles inválidos")
                texto_limpio = "".join(parts)
        else:
            texto_limpio = texto
            
    # Caso 4: Solo dígitos
    else:
        texto_limpio = texto

    return Decimal(sign + texto_limpio)


def validar_monto(texto: str) -> tuple[bool, str]:
    """Valida que un texto sea un monto monetario válido.
    Returns (is_valid, error_message)."""
    if not texto or not str(texto).strip():
        return False, "Ingresa un monto."
    try:
        valor = parsear_monto(texto)
        if valor <= 0:
            return False, "El monto debe ser mayor a cero."
        return True, ""
    except (InvalidOperation, ValueError):
        return False, "Ingresa un monto numérico válido."

def validar_texto_no_vacio(texto: str, campo: str) -> tuple[bool, str]:
    """Valida que un texto no esté vacío."""
    if not texto or not texto.strip():
        return False, f"El campo {campo} es obligatorio."
    return True, ""

def validar_entero_positivo(texto: str, campo: str) -> tuple[bool, str]:
    """Valida que un texto sea un entero positivo."""
    texto = texto.strip()
    if not texto:
        return False, f"El campo {campo} es obligatorio."
    try:
        valor = int(texto)
        if valor <= 0:
            return False, f"El campo {campo} debe ser mayor a cero."
        return True, ""
    except ValueError:
        return False, f"El campo {campo} debe ser un número entero."
