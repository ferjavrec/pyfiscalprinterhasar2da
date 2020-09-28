# -*- coding: iso-8859-1 -*-
import serial
import random
import time
import sys

def debugEnabled( *args ):
    print >>sys.stderr, " ".join( map(str, args) )

def debugDisabled( *args ):
    pass

debug = debugDisabled

class PrinterException(Exception):
    pass

class UnknownServerError(PrinterException):
    errorNumber = 1

class ComunicationError(PrinterException):
    errorNumber = 2

class PrinterStatusError(PrinterException):
    errorNumber = 3

class FiscalStatusError(PrinterException):
    errorNumber = 4

ServerErrors = [UnknownServerError, ComunicationError, PrinterStatusError, FiscalStatusError]

class ProxyError(PrinterException):
    errorNumber = 5

class FiscalDriver:
    WAIT_TIME = 10
    RETRIES = 4
    WAIT_CHAR_TIME = 0.1
    NO_REPLY_TRIES = 200

    fiscalStatusErrors = [#(1<<0 + 1<<7, "Memoria Fiscal llena"),
                          (1<<0, "Error en memoria fiscal"),
                          (1<<1, "Error de comprobación en memoria de trabajo"),
                          (1<<2, "Poca batería"),
                          (1<<3, "Comando no reconocido"),
                          (1<<4, "Campo de datos no válido"),
                          (1<<5, "Comando no válido para el estado fiscal"),
                          (1<<6, "Desbordamiento de totales"),
                          (1<<7, "Memoria Fiscal llena"),
                          (1<<8, "Memoria Fiscal casi llena"),
                          (1<<11, "Es necesario hacer un cierre de la jornada fiscal o se superó la cantidad máxima de tickets en una factura."),
                          ]

    printerStatusErrors = [(1<<2, "Error y/o falla de la impresora"),
                          (1<<3, "Impresora fuera de linea"),
##                        (1<<4, "Poco papel para la cinta de auditoría"),
##                        (1<<5, "Poco papel para comprobantes o tickets"),
                          (1<<6, "Buffer de impresora lleno"),
                          (1<<14, "Impresora sin papel"),
                          ]

    def __init__( self, deviceFile, speed = 9600 ):
        self._serialPort = serial.Serial( port = deviceFile, timeout = None, baudrate = speed )
        self._initSequenceNumber()

    def _initSequenceNumber( self ):
        self._sequenceNumber = random.randint( 0x20, 0x7f )

    def _incrementSequenceNumber( self ):
        # Avanzo el número de sequencia, volviendolo a 0x20 si pasó el limite
        self._sequenceNumber += 1
        if self._sequenceNumber > 0x7f:
            self._sequenceNumber = 0x20

    def _write( self, s ):
        if isinstance(s, unicode):
            s = s.encode("latin1")
        debug( "_write", ", ".join( [ "%x" % ord(c) for c in s ] ) )
        self._serialPort.write( s )

    def _read( self, count ):
        ret = self._serialPort.read( count )
        debug( "_read", ", ".join( [ "%x" % ord(c) for c in ret ] ) )
        return ret

    def __del__( self ):
        if hasattr(self, "_serialPort" ):
            try:
                self.close()
            except:
                pass

    def close( self ):
        try:
            self._serialPort.close()
        except:
            pass
        del self._serialPort

    def sendCommand( self, commandNumber, fields, skipStatusErrors = False ):
        message = chr(0x02) + chr( self._sequenceNumber ) + chr(commandNumber)
        if fields:
            message += chr(0x1c)
        message += chr(0x1c).join( fields )
        message += chr(0x03)
        checkSum = sum( [ord(x) for x in message ] )
        checkSumHexa = ("0000" + hex(checkSum)[2:])[-4:].upper()
        message += checkSumHexa
        reply = self._sendMessage( message )
        self._incrementSequenceNumber()
        return self._parseReply( reply, skipStatusErrors )

    def _parseReply( self, reply, skipStatusErrors ):
        r = reply[4:-1] # Saco STX <Nro Seq> <Nro Comando> <Sep> ... ETX
        fields = r.split( chr(28) )
        printerStatus = fields[0]
        fiscalStatus = fields[1]
        if not skipStatusErrors:
            self._parsePrinterStatus( printerStatus )
            self._parseFiscalStatus( fiscalStatus )
        return fields

    def _parsePrinterStatus( self, printerStatus ):
        x = int( printerStatus, 16 )
        for value, message in self.printerStatusErrors:
            if (value & x) == value:
                raise PrinterStatusError, message

    def _parseFiscalStatus( self, fiscalStatus ):
        x = int( fiscalStatus, 16 )
        for value, message in self.fiscalStatusErrors:
            if (value & x) == value:
                raise FiscalStatusError, message

    def _sendMessage( self, message ):
        # Envía el mensaje
        # @return reply Respuesta (sin el checksum)
        self._write( message )
        timeout = time.time() + self.WAIT_TIME
        retries = 0
        while 1:
            if time.time() > timeout:
                raise ComunicationError, "Expiró el tiempo de espera para una respuesta de la impresora. Revise la conexión."
            c = self._read(1)
            if len(c) == 0:
                continue
            if ord(c) in (0x12, 0x14): # DC2 o DC4
                # incrementar timeout
                timeout += self.WAIT_TIME
                continue
            if ord(c) == 0x15: # NAK
                if retries > self.RETRIES:
                    raise ComunicationError, "Falló el envío del comando a la impresora luego de varios reintentos"
                # Reenvío el mensaje
                self._write( message )
                timeout = time.time() + self.WAIT_TIME
                retries +=1
                continue
            if c == chr(0x02):# STX - Comienzo de la respuesta
                reply = c
                noreplyCounter = 0
                while c != chr(0x03): # ETX (Fin de texto)
                    c = self._read(1)
                    if not c:
                        noreplyCounter += 1
                        time.sleep(self.WAIT_CHAR_TIME)
                        if noreplyCounter > self.NO_REPLY_TRIES:
                            raise ComunicationError, "Fallo de comunicación mientras se recibía la respuesta de la impresora."
                    else:
                        noreplyCounter = 0
                        reply += c
                bcc = self._read(4) # Leo BCC
                if not self._checkReplyBCC( reply, bcc ):
                    # Mando un NAK y espero la respuesta de nuevo.
                    self._write( chr(0x15) )
                    timeout = time.time() + self.WAIT_TIME
                    retries += 1
                    if retries > self.RETRIES:
                        raise ComunicationError, "Fallo de comunicación, demasiados paquetes inválidos (bad bcc)."
                    continue
                elif reply[1] != chr( self._sequenceNumber ): # Los número de seq no coinciden
                    # Reenvío el mensaje
                    self._write( message )
                    timeout = time.time() + self.WAIT_TIME
                    retries +=1
                    if retries > self.RETRIES:
                        raise ComunicationError, "Fallo de comunicación, demasiados paquetes inválidos (mal sequence_number)."
                    continue
                else:
                    # Respuesta OK
                    break
        return reply

    def _checkReplyBCC( self, reply, bcc ):
        debug( "reply", reply, [ord(x) for x in reply] )
        checkSum = sum( [ord(x) for x in reply ] )
        debug( "checkSum", checkSum )
        checkSumHexa = ("0000" + hex(checkSum)[2:])[-4:].upper()
        debug( "checkSumHexa", checkSumHexa )
        debug( "bcc", bcc )
        return checkSumHexa == bcc.upper()

class HasarFiscalDriver( FiscalDriver ):
    fiscalStatusErrors = [(1<<0 + 1<<7, "Memoria Fiscal llena"),
                          (1<<0, "Error en memoria fiscal"),
                          (1<<1, "Error de comprobación en memoria de trabajo"),
                          (1<<2, "Poca batería"),
                          (1<<3, "Comando no reconocido"),
                          (1<<4, "Campo de datos no válido"),
                          (1<<5, "Comando no válido para el estado fiscal"),
                          (1<<6, "Desbordamiento de totales"),
                          (1<<7, "Memoria Fiscal llena"),
                          (1<<8, "Memoria Fiscal casi llena"),
                          (1<<11, "Es necesario hacer un cierre de la jornada fiscal o se superó la cantidad máxima de tickets en una factura."),
                          ]

    printerStatusErrors = [(1<<2, "Error y/o falla de la impresora"),
                          (1<<3, "Impresora fuera de linea"),
##                        (1<<4, "Poco papel para la cinta de auditoría"),
##                        (1<<5, "Poco papel para comprobantes o tickets"),
                          (1<<6, "Buffer de impresora lleno"),
                          (1<<8, "Tapa de impresora abierta"),
                          ]

    ACK = chr(0x06)
    NAK = chr(0x15)
    STATPRN = chr(0xa1)

    def _initSequenceNumber( self ):
        self._sequenceNumber = random.randint( 0x20, 0x7f )
        if self._sequenceNumber % 2:
            self._sequenceNumber -= 1

    def _incrementSequenceNumber( self ):
        # Avanzo el número de sequencia, volviendolo a 0x20 si pasó el limite
        self._sequenceNumber += 2
        if self._sequenceNumber > 0x7f:
            self._sequenceNumber = 0x20

    def _sendAndWaitAck( self, message, count = 0 ):
        if count > 10:
            raise ComunicationError, "Demasiados NAK desde la impresora. Revise la conexión."
        self._write( message )
        timeout = time.time() + self.WAIT_TIME
        while 1:
            if time.time() > timeout:
                raise ComunicationError, "Expiró el tiempo de espera para una respuesta de la impresora. Revise la conexión."
            c = self._read(1)
            if len(c) == 0:
                continue
            if c == self.ACK:
                return True
            if c == self.NAK:
                return self._sendAndWaitAck( message, count + 1 )

    def _sendMessage( self, message ):
        # Envía el mensaje
        # @return reply Respuesta (sin el checksum)
        self._sendAndWaitAck( message )
        timeout = time.time() + self.WAIT_TIME
        retries = 0
        while 1:
            if time.time() > timeout:
                raise ComunicationError, "Expiró el tiempo de espera para una respuesta de la impresora. Revise la conexión."
            c = self._read(1)
            if len(c) == 0:
                continue
            if ord(c) in (0x12, 0x14): # DC2 o DC4
                # incrementar timeout
                timeout += self.WAIT_TIME
                continue
            if c == chr(0x02):# STX - Comienzo de la respuesta
                reply = c
                noreplyCounter = 0
                while c != chr(0x03): # ETX (Fin de texto)
                    c = self._read(1)
                    if not c:
                        noreplyCounter += 1
                        time.sleep(self.WAIT_CHAR_TIME)
                        if noreplyCounter > self.NO_REPLY_TRIES:
                            raise ComunicationError, "Fallo de comunicación mientras se recibía la respuesta de la impresora."
                    else:
                        noreplyCounter = 0
                        reply += c
                bcc = self._read(4) # Leo BCC
                if not self._checkReplyBCC( reply, bcc ):
                    # Mando un NAK y espero la respuesta de nuevo.
                    self._write( self.NAK )
                    timeout = time.time() + self.WAIT_TIME
                    retries += 1
                    if retries > self.RETRIES:
                        raise ComunicationError, "Fallo de comunicación, demasiados paquetes inválidos (bad bcc)."
                    continue
                elif reply[1] != chr( self._sequenceNumber ): # Los número de seq no coinciden
                    # Reenvío el mensaje
                    self._write( self.ACK )
                    #self._sendAndWaitAck( message )
                    timeout = time.time() + self.WAIT_TIME
                    retries +=1
                    if retries > self.RETRIES:
                        raise ComunicationError, "Fallo de comunicación, demasiados paquetes inválidos (bad sequenceNumber)."
                    continue
                else:
                    # Respuesta OK
                    self._write( self.ACK )
                    break
        return reply
