# coding=utf-8
import sys
from hasar2GenPrinter import Hasar2GenPrinter


def cargarDatosCliente(p):
	p.cargarDatosCliente('Fernando Recci', '20223606173', p.IVA_TYPE_RESPONSABLE_MONOTRIBUTO,
						 p.DOC_TYPE_CUIT, 'Malere 885 - Azul')

def imprimirTicket(p):
	# TICKET A consumidor final
	p.abrirTicket()
	p.imprimirTextoFiscal(p.DOBLE_ANCHO, 'Hasta agotar stock ...')
	p.imprimirItem('coca cola x 1500cm', 1, 167.0, p.GRAVADO, 21, p.II_VARIBLE_KIVA, 0,
						p.MODO_PRECIO_BASE, codigoproducto='77877888')
	p.imprimirPago('Efectivo', 500, 'PAGAR', adicional='EFECTIVO')
	p.cerrarDocumento()


def imprimirFacturaA(p):
	p.cargarDatosCliente('Fernando Recci','20223606173', p.IVA_TYPE_RESPONSABLE_INSCRIPTO,
							p.DOC_TYPE_CUIT, 'Malere 885 - Azul')

	p.abrirTicketFactura('A')
	p.imprimirItem('coca cola x 1500cm', 1, 167.0, p.GRAVADO, 21, p.II_VARIBLE_KIVA, 0, p.MODO_PRECIO_BASE,
					 codigoproducto='77877888')

	p.imprimirSubtotal(impresion=p.NO_IMPRIME_SUBTOTAL)

	p.imprimirPago('Efectivo', 500, 'PAGAR', adicional=p.EFECTIVO)
	p.cerrarDocumento()





if __name__ == "__main__":
	print "Usando driver de Hasar2Gen - by GENEOS"
	printer = Hasar2GenPrinter(deviceFile="COM31")


	#imprimirTicket(printer)
	#imprimirFacturaA(printer)
	#printer.cancelarCualquierDocumento()
	#print printer.consultarFechaHora()
	#print printer.cerrarJornadaFiscal('Z')
	#print printer.configurarFechaHora()
	#print printer.configurarZona(1,'2','LA CATEDRAL', printer.ESTACION_POR_DEFECTO, printer.ZONA_FANTASIA)
	#print printer.configurarZona(1, '0', 'Malere 885 - Azul', printer.ESTACION_POR_DEFECTO, printer.ZONA_DOMICILIO_EMISOR)
	#print printer.consultarZona(1, printer.ESTACION_POR_DEFECTO, printer.ZONA_DOMICILIO_EMISOR)

	#print printer.copiarComprobante(printer.CPROB_TIQUE,'5')
	#print printer.pedirReimpresion()

	cargarDatosCliente(printer)
	#print printer.abrirTicketNC('B')
	#printer.abrirTicketFactura('B')

	#printer.imprimirItem('coca cola x 1500cm', 1, 167.0, printer.GRAVADO, 21, printer.II_VARIBLE_KIVA, 0, printer.MODO_PRECIO_BASE,
	#			   codigoproducto='77877888')
	#printer.imprimirPago('Efectivo', 500, 'PAGAR', adicional=printer.EFECTIVO)
	#printer.cerrarDocumento()

	#print printer.consultarUltimoNumero(printer.CPROB_TIQUE)

	#print printer.imprimirSubtotal(impresion=printer.IMPRIME_SUBTOTAL)



