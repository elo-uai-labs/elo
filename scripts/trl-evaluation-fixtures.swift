// Synthetic held-out OCR sheets; no user images or corporate documents.
import Foundation
import AppKit
import ImageIO
import CoreGraphics
let letter = "RELATORIO SINTETICO DE CONFERENCIA\nDocumento de teste sem validade comercial\nContrato CTR-701 - Fornecedor FOR-701\nEmissao: 14/06/2027\nValor registrado: R$ 845,60\nSituacao: revisao humana pendente\nNenhum pagamento comprovado neste documento"
let table = "QUADRO SINTETICO DE PARCELAS\nItem        Quantidade        Valor\nServico A   2                 120,00\nServico B   3                 210,00\nTotal registrado              330,00\nValores ficticios para conferencia"
let accented = "AVALIAÇÃO SINTÉTICA\nRevisão de evidências e atribuições\nSituação: documentação incompleta\nResponsável fictício: João de Sá\nA conclusão exige análise humana"
func make(_ text: String, blank: Bool = false, degraded: Bool = false) -> CGImage {
 let w=1600, h=1000
 let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:w,pixelsHigh:h,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
 NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:bitmap)
 NSColor.white.setFill();NSRect(x:0,y:0,width:w,height:h).fill()
 if !blank {
  let attrs:[NSAttributedString.Key:Any] = [.font:NSFont.monospacedSystemFont(ofSize:degraded ? 0.5:32,weight:.regular),.foregroundColor:NSColor.black]
  for (i,line) in text.components(separatedBy:"\n").enumerated() {(line as NSString).draw(at:NSPoint(x:70,y:850-i*90),withAttributes:attrs)}
 }
 NSGraphicsContext.restoreGraphicsState();return bitmap.cgImage!
}
func encoded(_ img:CGImage,_ type:CFString,_ quality:Double=0.95)->Data {
 let output=NSMutableData();let dst=CGImageDestinationCreateWithData(output,type,1,nil)!
 CGImageDestinationAddImage(dst,img,[kCGImageDestinationLossyCompressionQuality:quality] as CFDictionary);CGImageDestinationFinalize(dst);return output as Data
}
func pdf(_ images:[CGImage])->Data {
 let output=NSMutableData();let consumer=CGDataConsumer(data:output as CFMutableData)!;var bounds=CGRect(x:0,y:0,width:800,height:500)
 let context=CGContext(consumer:consumer,mediaBox:&bounds,nil)!
 for image in images {context.beginPDFPage(nil);context.draw(image,in:bounds);context.endPDFPage()};context.closePDF();return output as Data
}
let items:[String:Data] = ["letter.png":encoded(make(letter),"public.png" as CFString),"table.png":encoded(make(table),"public.png" as CFString),"accents.png":encoded(make(accented),"public.png" as CFString),"compressed.jpg":encoded(make(letter),"public.jpeg" as CFString,0.35),"two-pages.pdf":pdf([make(letter),make(table)]),"blank.png":encoded(make("",blank:true),"public.png" as CFString),"degraded.png":encoded(make(letter,degraded:true),"public.png" as CFString)]
let result=items.mapValues{$0.base64EncodedString()}
FileHandle.standardOutput.write(try JSONEncoder().encode(result))
