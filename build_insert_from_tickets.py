from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
CARPETAS = ("Facturas", "Facturas_con_errores")
ARCHIVO_SQL = ROOT / "insertUnderlineTickets.sql"
ARCHIVO_ERRORES = ROOT / "errores.txt"

CENTAVO = Decimal("0.01")
IVA_TIPO = Decimal("0.21")


def dinero(valor):
    """Redondea una cantidad a dos decimales como una factura."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def numero(valor):
    """Convierte números escritos con punto o coma decimal."""
    texto = valor.strip()
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", texto):
        raise ValueError("formato numérico no válido")
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation as error:
        raise ValueError("formato numérico no válido") from error


def extraer_numero(texto, campo, errores):
    if not texto:
        errores.append("Falta el campo obligatorio: " + campo)
        return None
    try:
        return numero(texto)
    except ValueError:
        errores.append("Número no válido en " + campo + ": " + repr(texto))
        return None


def parsear_ticket_impreso(texto):
    lineas = texto.splitlines()
    datos = {}
    productos = []

    for linea in lineas:
        coincidencia = re.search(r"\bCIF:\s*([A-Za-z0-9-]+)", linea, re.IGNORECASE)
        if coincidencia:
            datos["cif"] = coincidencia.group(1).upper()

        coincidencia = re.search(
            r"Fecha:\s*(\d{2}/\d{2}/\d{4}).*?Hora:\s*(\d{2}:\d{2})",
            linea,
            re.IGNORECASE,
        )
        if coincidencia:
            datos["fecha"] = coincidencia.group(1)
            datos["hora"] = coincidencia.group(2)

        coincidencia = re.search(
            r"Cajero:\s*(\d+)\s*(?:-\s*(.+?))?\s*$", linea, re.IGNORECASE
        )
        if coincidencia:
            datos["codigo_cajero"] = coincidencia.group(1)
            if coincidencia.group(2):
                datos["nombre_cajero"] = coincidencia.group(2).strip()

        coincidencia = re.search(r"Ticket:\s*(\d+)", linea, re.IGNORECASE)
        if coincidencia:
            datos["ticket"] = coincidencia.group(1)

        coincidencia = re.match(
            r"^\s*(\d+(?:[.,]\d+)?)\s+(.+?)\s+"
            r"(\d+(?:[.,]\d{1,2})?)\s*€\s*$",
            linea,
        )
        if coincidencia:
            productos.append(
                {
                    "cantidad": coincidencia.group(1),
                    "producto": coincidencia.group(2).strip(),
                    "importe": coincidencia.group(3),
                }
            )

        coincidencia = re.search(r"\bSUBTOTAL\s+([\d.,]+)\s*€", linea, re.IGNORECASE)
        if coincidencia:
            datos["subtotal"] = coincidencia.group(1)

        coincidencia = re.search(
            r"\bIVA(?:\s*\([^)]*\))?\s+([\d.,]+)\s*€", linea, re.IGNORECASE
        )
        if coincidencia:
            datos["iva"] = coincidencia.group(1)

        coincidencia = re.search(
            r"\bTOTAL A PAGAR\s+([\d.,]+)\s*€", linea, re.IGNORECASE
        )
        if coincidencia:
            datos["total"] = coincidencia.group(1)

        coincidencia = re.search(
            r"FORMA DE PAGO:\s*(.+?)\s*$", linea, re.IGNORECASE
        )
        if coincidencia:
            datos["pago"] = coincidencia.group(1).strip().upper()

    primera_linea = next((linea.strip() for linea in lineas if linea.strip()), "")
    datos["sucursal"] = primera_linea
    datos["productos"] = productos
    return datos


def parsear_ticket_etiquetado(texto):
    datos = {"productos": []}
    campos = {}
    producto_actual = None
    etiquetas = {
        "cif": "cif",
        "fecha": "fecha",
        "hora": "hora",
        "cajero": "codigo_cajero",
        "nombre cajero": "nombre_cajero",
        "ticket": "ticket",
        "subtotal": "subtotal",
        "iva": "iva",
        "total": "total",
        "pago": "pago",
        "forma de pago": "pago",
    }

    for linea in texto.splitlines():
        coincidencia = re.match(r"^\s*([^:]+):\s*(.*?)\s*$", linea)
        if not coincidencia:
            continue
        etiqueta = coincidencia.group(1).strip().casefold()
        valor = coincidencia.group(2).strip()

        if etiqueta == "producto":
            producto_actual = {"producto": valor}
            datos["productos"].append(producto_actual)
        elif etiqueta in ("cantidad", "precio", "importe"):
            if producto_actual is None:
                datos.setdefault("errores", []).append(
                    "Campo " + etiqueta + " encontrado antes de un producto"
                )
            else:
                producto_actual[etiqueta] = valor
        elif etiqueta in etiquetas:
            campo = etiquetas[etiqueta]
            if campo in campos:
                datos.setdefault("errores", []).append(
                    "Campo repetido: " + etiqueta
                )
            else:
                campos[campo] = valor

    primera_linea = next(
        (linea.strip() for linea in texto.splitlines() if linea.strip()), ""
    )
    datos["sucursal"] = primera_linea
    datos.update(campos)
    return datos


def validar_fecha_hora(datos, errores):
    fecha = datos.get("fecha", "")
    hora = datos.get("hora", "")
    fecha_valida = None
    hora_valida = None

    if fecha and re.fullmatch(r"\d{2}/\d{2}/\d{4}", fecha):
        try:
            fecha_valida = datetime.strptime(fecha, "%d/%m/%Y").date()
        except ValueError:
            pass
    if fecha and fecha_valida is None:
        errores.append("Fecha no válida: " + repr(fecha))

    if hora and re.fullmatch(r"\d{2}:\d{2}", hora):
        try:
            hora_valida = datetime.strptime(hora, "%H:%M").time()
        except ValueError:
            pass
    if hora and hora_valida is None:
        errores.append("Hora no válida: " + repr(hora))

    return fecha_valida, hora_valida


def validar_datos(datos, formato):
    errores = list(datos.get("errores", []))
    campos = (
        "sucursal",
        "cif",
        "fecha",
        "hora",
        "codigo_cajero",
        "nombre_cajero",
        "ticket",
        "subtotal",
        "iva",
        "total",
        "pago",
    )
    for campo in campos:
        if not datos.get(campo):
            errores.append("Falta el campo obligatorio: " + campo)

    if datos.get("cif") and not re.fullmatch(
        r"[A-Z0-9-]+", datos["cif"], re.IGNORECASE
    ):
        errores.append("CIF no válido: " + repr(datos["cif"]))
    if datos.get("codigo_cajero") and not re.fullmatch(
        r"\d+", datos["codigo_cajero"]
    ):
        errores.append("Código de cajero no válido: " + repr(datos["codigo_cajero"]))
    if datos.get("ticket") and not re.fullmatch(r"\d+", datos["ticket"]):
        errores.append("Número de ticket no válido: " + repr(datos["ticket"]))

    fecha, hora = validar_fecha_hora(datos, errores)

    productos = datos.get("productos", [])
    if not productos:
        errores.append("La factura no contiene productos")

    productos_validos = []
    for indice, producto in enumerate(productos, start=1):
        etiqueta = "producto " + str(indice)
        nombre = producto.get("producto", "").strip()
        if not nombre:
            errores.append("Falta la descripción del " + etiqueta)

        cantidad = extraer_numero(producto.get("cantidad", ""), etiqueta + " (cantidad)", errores)
        importe = extraer_numero(producto.get("importe", ""), etiqueta + " (importe)", errores)

        if formato == "etiquetado":
            precio = extraer_numero(producto.get("precio", ""), etiqueta + " (precio)", errores)
        elif cantidad is not None and cantidad > 0 and importe is not None:
            precio = dinero(importe / cantidad)
        else:
            precio = None

        if cantidad is not None and cantidad <= 0:
            errores.append("La cantidad debe ser mayor que cero en " + etiqueta)
        if precio is not None and precio <= 0:
            errores.append("El precio debe ser mayor que cero en " + etiqueta)
        if importe is not None and importe < 0:
            errores.append("El importe no puede ser negativo en " + etiqueta)

        if cantidad is not None and precio is not None and importe is not None:
            if dinero(cantidad * precio) != dinero(importe):
                errores.append("La operación cantidad × precio no coincide en " + etiqueta)
            else:
                productos_validos.append(
                    {
                        "producto": nombre,
                        "cantidad": cantidad,
                        "precio": precio,
                        "importe": dinero(importe),
                    }
                )

    subtotal = extraer_numero(datos.get("subtotal", ""), "subtotal", errores)
    iva = extraer_numero(datos.get("iva", ""), "IVA", errores)
    total = extraer_numero(datos.get("total", ""), "total", errores)

    if subtotal is not None and subtotal < 0:
        errores.append("El subtotal no puede ser negativo")
    if iva is not None and iva < 0:
        errores.append("El IVA no puede ser negativo")
    if total is not None and total < 0:
        errores.append("El total no puede ser negativo")

    if productos and all("importe" in producto for producto in productos):
        importes = []
        for producto in productos:
            try:
                importes.append(dinero(numero(producto["importe"])))
            except ValueError:
                break
        if len(importes) == len(productos) and subtotal is not None:
            if sum(importes, Decimal("0.00")) != dinero(subtotal):
                errores.append("El subtotal no coincide con la suma de los importes")

    if subtotal is not None and iva is not None:
        if dinero(subtotal * IVA_TIPO) != dinero(iva):
            errores.append("El IVA no coincide con el 21% del subtotal")
    if subtotal is not None and iva is not None and total is not None:
        if dinero(subtotal + iva) != dinero(total):
            errores.append("El total no coincide con subtotal + IVA")

    datos_validados = None
    if not errores:
        datos_validados = {
            "sucursal": datos["sucursal"].strip(),
            "cif": datos["cif"].upper(),
            "fecha": fecha,
            "hora": hora,
            "codigo_cajero": datos["codigo_cajero"],
            "nombre_cajero": datos["nombre_cajero"].strip(),
            "ticket": datos["ticket"],
            "productos": productos_validos,
            "subtotal": dinero(subtotal),
            "iva": dinero(iva),
            "total": dinero(total),
            "pago": datos["pago"].strip().upper(),
        }

    return datos_validados, errores


def leer_factura(ruta):
    try:
        texto = ruta.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        return {"ruta": ruta, "datos": None, "errores": ["No se pudo leer el archivo: " + str(error)]}

    if not texto.strip():
        return {"ruta": ruta, "datos": None, "errores": ["Archivo vacío"]}

    if re.search(r"^\s*Producto\s*:", texto, re.IGNORECASE | re.MULTILINE):
        datos = parsear_ticket_etiquetado(texto)
        formato = "etiquetado"
    elif re.search(r"^\s*FORMA DE PAGO\s*:", texto, re.IGNORECASE | re.MULTILINE):
        datos = parsear_ticket_impreso(texto)
        formato = "impreso"
    else:
        return {
            "ruta": ruta,
            "datos": None,
            "errores": ["Formato de factura no reconocido"],
        }

    datos_validados, errores = validar_datos(datos, formato)
    return {
        "ruta": ruta,
        "datos": datos_validados,
        "errores": errores,
        "ticket_detectado": datos.get("ticket"),
    }


def revisar_duplicados_y_cajeros(facturas):
    validas = [factura for factura in facturas if factura["datos"] is not None]

    nombres_por_codigo = {}
    for factura in validas:
        datos = factura["datos"]
        clave = (datos["cif"], datos["codigo_cajero"])
        nombres_por_codigo.setdefault(clave, set()).add(datos["nombre_cajero"].casefold())

    for factura in validas:
        datos = factura["datos"]
        clave = (datos["cif"], datos["codigo_cajero"])
        if len(nombres_por_codigo[clave]) > 1:
            factura["errores"].append(
                "El código de cajero "
                + datos["codigo_cajero"]
                + " está asociado a nombres diferentes"
            )

    vistos = {}
    for factura in facturas:
        datos = factura["datos"]
        if datos is None:
            continue
        clave = (datos["cif"], datos["ticket"])
        if clave in vistos:
            factura["errores"].append(
                "Ticket duplicado "
                + datos["ticket"]
                + "; ya aparece en "
                + vistos[clave]
            )
        else:
            vistos[clave] = str(factura["ruta"].relative_to(ROOT))


def sql_texto(valor):
    return "'" + str(valor).replace("\\", "\\\\").replace("'", "''") + "'"


def sql_decimal(valor):
    return format(valor, "f")


def generar_sql(facturas):
    lineas = [
        "-- Generado por build_insert_from_tickets.py",
        "START TRANSACTION;",
    ]

    for factura in facturas:
        datos = factura["datos"]
        if datos is None or factura["errores"]:
            continue

        fecha = datos["fecha"].strftime("%Y-%m-%d")
        hora = datos["hora"].strftime("%H:%M:%S")
        cif = sql_texto(datos["cif"])
        ticket = sql_texto(datos["ticket"])
        codigo = sql_texto(datos["codigo_cajero"])

        lineas.extend(
            [
                "",
                "INSERT IGNORE INTO sucursal (nombre,cif) VALUES ("
                + sql_texto(datos["sucursal"])
                + ","
                + cif
                + ");",
                "SET @s=(SELECT id_sucursal FROM sucursal WHERE cif="
                + cif
                + " LIMIT 1);",
                "INSERT IGNORE INTO empleado (codigo,nombre,id_sucursal) VALUES ("
                + codigo
                + ","
                + sql_texto(datos["nombre_cajero"])
                + ",@s);",
                "SET @e=(SELECT id_empleado FROM empleado WHERE codigo="
                + codigo
                + " AND id_sucursal=@s LIMIT 1);",
                "INSERT IGNORE INTO ticket "
                "(numero_ticket,fecha,hora,subtotal,iva,total,id_sucursal,id_empleado) "
                "VALUES ("
                + ticket
                + ","
                + sql_texto(fecha)
                + ","
                + sql_texto(hora)
                + ","
                + sql_decimal(datos["subtotal"])
                + ","
                + sql_decimal(datos["iva"])
                + ","
                + sql_decimal(datos["total"])
                + ",@s,@e);",
                "SET @t=(SELECT id_ticket FROM ticket WHERE numero_ticket="
                + ticket
                + " AND id_sucursal=@s LIMIT 1);",
                "DELETE FROM ticket_linea WHERE id_ticket=@t;",
            ]
        )

        for producto in datos["productos"]:
            descripcion = sql_texto(producto["producto"])
            lineas.extend(
                [
                    "INSERT IGNORE INTO producto (descripcion) VALUES ("
                    + descripcion
                    + ");",
                    "SET @p=(SELECT id_producto FROM producto WHERE descripcion="
                    + descripcion
                    + " LIMIT 1);",
                    "INSERT INTO ticket_linea "
                    "(id_ticket,id_producto,cantidad,precio_unitario,importe) "
                    "VALUES (@t,@p,"
                    + sql_decimal(producto["cantidad"])
                    + ","
                    + sql_decimal(producto["precio"])
                    + ","
                    + sql_decimal(producto["importe"])
                    + ");",
                ]
            )

        lineas.append(
            "INSERT INTO pago (id_ticket,metodo_pago,importe) VALUES "
            "(@t,"
            + sql_texto(datos["pago"])
            + ","
            + sql_decimal(datos["total"])
            + ") ON DUPLICATE KEY UPDATE "
            "metodo_pago=VALUES(metodo_pago),importe=VALUES(importe);"
        )

    lineas.extend(["", "COMMIT;", ""])
    return "\n".join(lineas)


def main():
    rutas = []
    for carpeta in CARPETAS:
        directorio = ROOT / carpeta
        if not directorio.is_dir():
            raise FileNotFoundError("No existe la carpeta requerida: " + str(directorio))
        rutas.extend(sorted(directorio.glob("*.txt")))

    facturas = [leer_factura(ruta) for ruta in rutas]
    revisar_duplicados_y_cajeros(facturas)

    validas = [factura for factura in facturas if not factura["errores"]]
    rechazadas = [factura for factura in facturas if factura["errores"]]

    ARCHIVO_SQL.write_text(generar_sql(validas), encoding="utf-8")
    contenido_errores = []
    for factura in rechazadas:
        ruta = str(factura["ruta"].relative_to(ROOT))
        motivos = "; ".join(factura["errores"])
        contenido_errores.append(ruta + ": " + motivos)
    ARCHIVO_ERRORES.write_text(
        "\n".join(contenido_errores) + ("\n" if contenido_errores else ""),
        encoding="utf-8",
    )

    print("Archivos encontrados: " + str(len(rutas)))
    print("Facturas válidas: " + str(len(validas)))
    print("Facturas rechazadas: " + str(len(rechazadas)))


if __name__ == "__main__":
    main()