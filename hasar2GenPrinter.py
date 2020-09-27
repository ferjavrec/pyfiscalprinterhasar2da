# -*- coding: iso-8859-1 -*-
import datetime
import string
import logging
from array import array
import epsonFiscalDriver


class ValidationError(Exception):
    pass


class FiscalPrinterError(Exception):
    pass


class PrinterException(RuntimeError):
    pass


def str_skip_bytes(s, dels):
    """
    """
    if not dels:
        return s
    return ''.join(c for i, c in enumerate(s) if i not in dels)



def valid_utf8_bytes(s):
    """
    """
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    bytearray = array('B', s)
    return str_skip_bytes(s, invalid_utf8_indexes(bytearray))


def invalid_utf8_indexes(bytes):
    """
    """
    skips = []
    i = 0
    len_bytes = len(bytes)
    while i < len_bytes:
        c1 = bytes[i]
        if c1 < 0x80:
            # U+0000 - U+007F - 7 bits
            i += 1
            continue
        try:
            c2 = bytes[i + 1]
            if ((c1 & 0xE0 == 0xC0) and (c2 & 0xC0 == 0x80)):
                # U+0080 - U+07FF - 11 bits
                c = (((c1 & 0x1F) << 6) |
                     (c2 & 0x3F))
                if c < 0x80:
                    # Overlong encoding
                    skips.extend([i, i + 1])
                i += 2
                continue
            c3 = bytes[i + 2]
            if ((c1 & 0xF0 == 0xE0) and
                    (c2 & 0xC0 == 0x80) and
                    (c3 & 0xC0 == 0x80)):
                # U+0800 - U+FFFF - 16 bits
                c = (((((c1 & 0x0F) << 6) |
                       (c2 & 0x3F)) << 6) |
                     (c3 & 0x3f))
                if ((c < 0x800) or (0xD800 <= c <= 0xDFFF)):
                    # Overlong encoding or surrogate.
                    skips.extend([i, i + 1, i + 2])
                i += 3
                continue
            c4 = bytes[i + 3]
            if ((c1 & 0xF8 == 0xF0) and
                    (c2 & 0xC0 == 0x80) and
                    (c3 & 0xC0 == 0x80) and
                    (c4 & 0xC0 == 0x80)):
                # U+10000 - U+10FFFF - 21 bits
                c = (((((((c1 & 0x0F) << 6) |
                         (c2 & 0x3F)) << 6) |
                       (c3 & 0x3F)) << 6) |
                     (c4 & 0x3F))
                if (c < 0x10000) or (c > 0x10FFFF):
                    # Overlong encoding or invalid code point.
                    skips.extend([i, i + 1, i + 2, i + 3])
                i += 4
                continue
        except IndexError:
            pass
        skips.append(i)
        i += 1
    return skips


def formatText(text):
    text = valid_utf8_bytes(text)
    text = text.replace('á', 'a')
    text = text.replace('é', 'e')
    text = text.replace('í', 'i')
    text = text.replace('ó', 'o')
    text = text.replace('ú', 'u')
    text = text.replace('Á', 'A')
    text = text.replace('É', 'E')
    text = text.replace('Í', 'I')
    text = text.replace('Ó', 'O')
    text = text.replace('Ú', 'U')
    text = text.replace('Ä', 'A')
    text = text.replace('Ë', 'E')
    text = text.replace('Ï', 'I')
    text = text.replace('Ö', 'O')
    text = text.replace('Ü', 'U')
    text = text.replace('ä', 'a')
    text = text.replace('ë', 'e')
    text = text.replace('ï', 'i')
    text = text.replace('ö', 'o')
    text = text.replace('ü', 'u')
    text = text.replace('ñ', 'n')
    text = text.replace('Ñ', 'N')
    text = text.replace('\\', ' ')
    text = text.replace('\'', ' ')
    text = text.replace('º', ' ')
    text = text.replace('"', ' ')
    text = text.replace('|', ' ')
    text = text.replace('¿', ' ')
    text = text.replace('¡', ' ')
    text = text.replace('ª', ' ')
    return text



class Hasar2GenPrinter:
    # comandos para impresores fiscales Hasar 2da generacion
    DOC_TYPE_CUIT = 'C'
    DOC_TYPE_CUIL = 'L'
    DOC_TYPE_LE = '0'
    DOC_TYPE_LC = '1'
    DOC_TYPE_DNI = '2'
    DOC_TYPE_PASAPORTE = '3'
    DOC_TYPE_CEDULA = '4'
    DOC_TYPE_NINGUNO = ' '

    IVA_TYPE_RESPONSABLE_INSCRIPTO = 'I'
    IVA_TYPE_EXENTO = 'E'
    IVA_TYPE_NO_RESPONSABLE = 'A'
    IVA_TYPE_CONSUMIDOR_FINAL = 'C'
    IVA_TYPE_NO_CATEGORIZADO = 'T'
    IVA_TYPE_RESPONSABLE_MONOTRIBUTO = 'M'
    IVA_TYPE_MONOTRIBUTISTA_SOCIAL = 'S'
    IVA_TYPE_PEQUENIO_CONTRIBUYENTE_EVENTUAL = 'V'
    IVA_TYPE_PEQUENIO_CONTRIBUYENTE_EVENTUAL_SOCIAL = 'W'

    NO_GRAVADO = '1'
    EXENTO = '2'
    GRAVADO = '7'

    II_VARIBLE_KIVA = '0'
    II_VARIABLE_PORCENTUAL = '%'
    II_FIJO_KIVA = '+'
    II_FIJO_MONTO = '$'

    MODO_PRECIO_BASE = 'B'
    MODO_PRECIO_TOTAL = 'T'

    CAMBIO = '0'
    CARTADECREDITODOCUMENTARIO = '1'
    CARTADECREDITOSIMPLE = '2'
    CHEQUE = '3'
    CHEQUECANCELATORIOS = '4'
    CREDITODOCUMENTARIO = '5'
    CUENTACORRIENTE = '6'
    DEPOSITO = '7'
    EFECTIVO = '8'
    ENDOSODECHEQUE = '9'
    FACTURADECREDITO = '10'
    GARANTIABANCARIA = '11'
    GIRO = '12'
    LETRADECAMBIO = '13'
    MEDIODEPAGODECOMERCIOEXTERIOR = '14'
    ORDENDEPAGODOCUMENTARIA = '15'
    ORDENDEPAGOSIMPLE = '16'
    PAGOCONTRAREEMBOLSO = '17'
    REMESADOCUMENTARIA = '18'
    REMESASIMPLE = '19'
    TARJETADECREDITO = '20'
    TARJETADEDEBITO = '21'
    TICKET = '22'
    TRANSFERENCIABANCARIA = '23'
    TRANSFERENCIANOBANCARIA = '24'
    OTROSMEDIOSPAGO = '99'

    ATTRIB_TEXTO_NORMAL = '0'
    ATTRIB_BORRADO_TEXTO = '1'
    ATTRIB_DOBLE_ANCHO = '2'
    ATTRIB_CENTRADO = '4'
    ATTRIB_NEGRITA = '3'

    ESTACION_TICKET = 'T'
    ESTACION_POR_DEFECTO = 'D'

    ZONA_FANTASIA = 'F'
    ZONA_DOMICILIO_EMISOR = 'O'
    ZONA1_ENCABEZADO = 'H'
    ZONA2_ENCABEZADO = 'h'
    ZONA1_COLA = 'T'
    ZONA2_COLA = 't'

    CPROB_TIQUE_FACTURA_A = '81'
    CPROB_TIQUE_FACTURA_B = '82'
    CPROB_TIQUE = '83'
    CPROB_TIQUE_NC = '110'
    CPROB_TIQUE_FACTURA_C = '111'
    CPROB_TIQUE_NC_A = '112'
    CPROB_TIQUE_NC_B = '113'
    CPROB_TIQUE_NC_C = '114'
    CPROB_TIQUE_ND_A = '115'
    CPROB_TIQUE_ND_B = '116'
    CPROB_TIQUE_ND_C = '117'
    CPROB_TIQUE_FACTURA_M = '118'
    CPROB_TIQUE_NC_M = '119'
    CPROB_TIQUE_ND_M = '120'

    IMPRIME_SUBTOTAL = 'P'
    NO_IMPRIME_SUBTOTAL = 'N'

    DISPLAY_NO = '0'
    DISPLAY_SI = '1'
    DISPLAY_REP = '2'

    CMD_CONSULTAR_VERSION = 0x7F
    CMD_CONSULTAR_DATOS_INICIALIZACION = 0x73
    CMD_CERRAR_JORNADA_FISCAL = 0X39
    CMD_CONSULTAR_ESTADO = 0x2A
    CMD_ABRIR_DOCUMENTO = 0x40
    CMD_IMPRIMIR_ITEM = 0x42
    CMD_IMPRIMIR_PAGO = 0x44
    CMD_CERRAR_DOCUMENTO = 0x45
    CMD_IMPRIMIR_TEXTO_FISCAL = 0x41
    CMD_CARGAR_DATOS_CLIENTE = 0x62
    CMD_CANCELAR_CUALQUIER_DOC = 0x98
    CMD_CONSULTAR_FECHA_HORA = 0x59
    CMD_CONFIGURAR_FECHA_HORA = 0x58
    CMD_CONSULTAR_ZONA = 0x9F
    CMD_CONFIGURAR_ZONA = 0x9E
    CMD_COPIAR_COMPROBANTE = 0xAF
    CMD_PEDIR_REIMPRESION = 0x99
    CMD_ABRIR_CAJON_DINERO = 0x7B
    CMD_IMPRIME_SUBTOTAL = 0x43


    AVAILABLE_MODELS = ["250", "1000"]


    def __init__(self, deviceFile=None, speed=9600, model='1000', connectOnEveryCommand=False):
        try:
            deviceFile = deviceFile or 0
            self.driver = epsonFiscalDriver.HasarFiscalDriver(deviceFile, speed)
        except Exception, e:
            raise FiscalPrinterError("Imposible establecer comunicación.", e)
        self.model = model


    def _sendCommand(self, commandNumber, parameters=(), skipStatusErrors=False):
        commandString = ''
        try:
            commandString = "SEND|0x%x|%s|%s" % (commandNumber, skipStatusErrors and "T" or "F",
                str(parameters))
            logging.getLogger().info("sendCommand: %s" % commandString)
            ret = self.driver.sendCommand(commandNumber, parameters, skipStatusErrors)
            logging.getLogger().info("reply: %s" % ret)
            return ret
        except epsonFiscalDriver.PrinterException, e:
            logging.getLogger().error("epsonFiscalDriver.PrinterException: %s" % str(e))
            raise PrinterException("Error de la impresora fiscal: %s.\nComando enviado: %s" % \
                (str(e), commandString))



    #comandos para segunda generacion de hasar
    def consultarVersion(self):
        reply = self._sendCommand(self.CMD_CONSULTAR_VERSION)
        return reply

    def consultarDatosInicializacion(self):
        reply = self._sendCommand(self.CMD_CONSULTAR_DATOS_INICIALIZACION)
        return reply

    def cerrarJornadaFiscal(self, type):
        reply = self._sendCommand(self.CMD_CERRAR_JORNADA_FISCAL, [type])
        return reply

    def consultarEstado(self, codigocomprobante):
        reply = self._sendCommand(self.CMD_CONSULTAR_ESTADO, [codigocomprobante])
        return reply

    def consultarWarnings(self):
        ret = []
        reply = self._sendCommand(self.CMD_CONSULTAR_ESTADO, [], True)
        printerStatus = reply[0]
        x = int(printerStatus)
        if x != 0:
            if x == 8030:
                ret.append("Poco papel para la cinta de auditoría")
            if x == 8008:
                ret.append("Impresora fuera de linea")
            if x == 8100:
                ret.append("La tapa de la impresora esta mal cerrada/abierta")
            if x == 8004:
                ret.append("Error mecanico en impresora")
        return ret


    def abrirTicket(self):
        reply = self._sendCommand(self.CMD_ABRIR_DOCUMENTO, [self.CPROB_TIQUE])
        return reply


    def abrirTicketFactura(self, type):
        letra = str(type).upper()
        if letra == 'A':
            tipo = self.CPROB_TIQUE_FACTURA_A
        elif letra == 'B':
            tipo = self.CPROB_TIQUE_FACTURA_B
        elif letra == 'C':
            tipo = self.CPROB_TIQUE_FACTURA_C
        else:
            tipo = self.CPROB_TIQUE_FACTURA_M
        reply = self._sendCommand(self.CMD_ABRIR_DOCUMENTO, [tipo])
        return reply


    def abrirTicketNC(self, type):
        letra = str(type).upper()
        if letra == 'A':
            tipo = self.CPROB_TIQUE_NC_A
        elif letra == 'B':
            tipo = self.CPROB_TIQUE_NC_B
        elif letra == 'C':
            tipo = self.CPROB_TIQUE_NC_C
        else:
            tipo = self.CPROB_TIQUE_NC_M
        reply = self._sendCommand(self.CMD_ABRIR_DOCUMENTO, [tipo])
        return reply


    def abrirTicketND(self, type):
        letra = str(type).upper()
        if letra == 'A':
            tipo = self.CPROB_TIQUE_ND_A
        elif letra == 'B':
            tipo = self.CPROB_TIQUE_ND_B
        elif letra == 'C':
            tipo = self.CPROB_TIQUE_ND_C
        else:
            tipo = self.CPROB_TIQUE_ND_M
        reply = self._sendCommand(self.CMD_ABRIR_DOCUMENTO, [tipo])
        return reply



    def imprimirItem(self, descripcion, cantidad, preciounitario, condicioniva, alicuotaiva, impuestosinternos,
                     magnitudimpuestointerno, modobasetotal, unidadreferencia='1', negativo=False, codigoproducto='',
                     codigointerno='', unidadmedida='7'):
        if negativo:
            signo = 'm'
        else:
            signo = 'M'

        cantidadStr = str(float(cantidad)).replace(',', '.')
        precioUnit = preciounitario
        preciounitarioStr = str(precioUnit).replace(",", ".")
        ivaStr = str(float(alicuotaiva)).replace(",", ".")
        magnitudimpuestointernoStr = str(float(magnitudimpuestointerno)).replace(",", ".")
        mododisplay = '0'
        reply = self._sendCommand(self.CMD_IMPRIMIR_ITEM,
                                  [formatText(descripcion), cantidadStr, preciounitarioStr, condicioniva, ivaStr, signo,
                                   impuestosinternos, magnitudimpuestointernoStr, mododisplay, modobasetotal,
                                   unidadreferencia, codigoproducto, codigointerno, unidadmedida])
        return reply


    def imprimirPago(self, descripcion, monto, operacion, adicional='', tipo_pago=EFECTIVO):
        montoStr = str(monto).replace(",", ".")
        if str(operacion) == 'PAGAR':
            cod_operacion = 'T'
        else:
            cod_operacion = 'R'
        display_no = '0'
        reply = self._sendCommand(self.CMD_IMPRIMIR_PAGO,
                                  [formatText(descripcion), montoStr, cod_operacion,
                                   display_no, adicional, tipo_pago, '0', ''])
        return reply



    def imprimirTextoFiscal(self, atributo, texto):
        reply = self._sendCommand(self.CMD_IMPRIMIR_TEXTO_FISCAL, [atributo, formatText(texto), '0'])
        return reply


    def cerrarDocumento(self, copias='0', direcciondemail=''):
        reply = self._sendCommand(self.CMD_CERRAR_DOCUMENTO, [copias, direcciondemail])
        return reply


    def cargarDatosCliente(self, razonsocial, numerodocumento, responsabilidadIVA, tipodocumento,
                           domicilio, datosadicionales1='', datosadicionales2='', datosadicionales3=''):
        doc = numerodocumento.replace("-", "").replace(".", "")
        if doc and tipodocumento != "3" and filter(lambda x: x not in string.digits, doc):
            doc, tipodocumento = " ", " "
        if not doc.strip():
            tipodocumento = " "

        if responsabilidadIVA != "C" and (not doc or tipodocumento != self.DOC_TYPE_CUIT):
            raise ValidationError("Error, si el tipo de IVA del cliente NO es consumidor final, "
                "debe ingresar su número de CUIT.")

        parametros = [formatText(razonsocial),
                       doc or " ",
                       responsabilidadIVA,
                       tipodocumento or " ",
                       formatText(domicilio) or " ",
                       formatText(datosadicionales1) or " ",
                       formatText(datosadicionales2) or " ",
                       formatText(datosadicionales3) or " "
                       ]
        self._sendCommand(self.CMD_CARGAR_DATOS_CLIENTE, parametros)


    def cancelarCualquierDocumento(self):
        try:
            self._sendCommand(self.CMD_CANCELAR_CUALQUIER_DOC)
        except:
            pass


    def consultarFechaHora(self):
        reply = self._sendCommand(self.CMD_CONSULTAR_FECHA_HORA)
        return reply


    def configurarFechaHora(self):
        fecha = datetime.datetime.today().date().strftime('%y%m%d')
        hora = datetime.datetime.today().time().strftime('%H%M%S')
        reply = self._sendCommand(self.CMD_CONFIGURAR_FECHA_HORA, [fecha, hora])
        return reply


    def consultarZona(self, numerolinea, estacion, identificadorzona):
        reply = self._sendCommand(self.CMD_CONSULTAR_ZONA, [str(numerolinea), estacion, identificadorzona])
        return reply


    def configurarZona(self, numerolinea, atributos, descripcion, estacion, identificadorzona):
        reply = self._sendCommand(self.CMD_CONFIGURAR_ZONA, [str(numerolinea), atributos, formatText(descripcion),
                                                             estacion, identificadorzona])
        return reply


    def copiarComprobante(self, codcomprobante, numerocomprobante, imprimir='S'):
        reply = self._sendCommand(self.CMD_COPIAR_COMPROBANTE, [codcomprobante,numerocomprobante,imprimir])
        return reply


    def pedirReimpresion(self):
        reply = self._sendCommand(self.CMD_PEDIR_REIMPRESION)
        return reply


    def abriCajonDinero(self):
        reply = ''
        if self.model == '250':
            reply = self._sendCommand(self.CMD_ABRIR_CAJON_DINERO)
        return reply


    def consultarUltimoNumero(self, codigocomprobante):
        ret = ''
        reply = self._sendCommand(self.CMD_CONSULTAR_ESTADO, [codigocomprobante])
        if len(reply) > 1:
            ret = reply[6]
        return ret


    def imprimirSubtotal(self, impresion=IMPRIME_SUBTOTAL, mododisplay=DISPLAY_NO):
        reply = self._sendCommand(self.CMD_IMPRIME_SUBTOTAL, [impresion, mododisplay])
        return reply


    def __del__(self):
        try:
            self.close()
        except:
            pass

    def close(self):
        self.driver.close()
        self.driver = None
