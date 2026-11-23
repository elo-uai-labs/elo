// Independently authored synthetic holdout. Expected text is authored before OCR.
import Foundation
import AppKit
import ImageIO
import CoreGraphics
struct Spec {let name:String;let text:String;let font:String;let size:CGFloat;let format:String;let bad:Bool}
let specs:[Spec] = [
 Spec(name:"memorandum",text:"MEMORANDO SINTÉTICO\nUnidade fictícia: Núcleo Aurora\nProtocolo: 8642/2028\nSolicitação recebida em 23/08/2028\nPrazo de resposta: 12 dias úteis\nDocumento criado apenas para teste",font:"Helvetica",size:34,format:"png",bad:false),
 Spec(name:"inventory",text:"INVENTÁRIO FICTÍCIO\nMaterial          Quantidade\nCadeiras          24\nMesas             16\nArmários          8\nConferência física pendente",font:"Menlo",size:31,format:"png",bad:false),
 Spec(name:"credit",text:"NOTA SINTÉTICA DE AJUSTE\nValor anterior: R$ 7.250,00\nAbatimento: R$ 125,50\nSaldo informado: R$ 7.124,50\nNão comprova pagamento",font:"Times New Roman",size:38,format:"jpg",bad:false),
 Spec(name:"schedule",text:"CRONOGRAMA FICTÍCIO\nEtapa Alfa: 03/02/2029\nEtapa Beta: 27/03/2029\nEtapa Gama: sem data definida\nAprovação ainda não registrada",font:"Helvetica",size:32,format:"pdf",bad:false),
 Spec(name:"responsibility",text:"ATRIBUIÇÕES SINTÉTICAS\nPreparação: Cecília Gonçalves\nConferência: André Nóbrega\nRevisão: Lívia Assunção\nNenhuma assinatura foi coletada",font:"Helvetica",size:36,format:"png",bad:false),
 Spec(name:"minutes",text:"ATA FICTÍCIA DE REUNIÃO\nParticipantes previstos: 18\nParticipantes presentes: 13\nAusências justificadas: 5\nDeliberação: solicitar documentação\nNão houve decisão sobre impactos",font:"Times New Roman",size:36,format:"jpg",bad:false),
 Spec(name:"delivery",text:"CONTROLE SINTÉTICO DE ENTREGA\nLote: AZ-882\nUnidades previstas: 460\nUnidades recebidas: 452\nDivergência registrada: 8\nConferência qualitativa pendente",font:"Menlo",size:30,format:"png",bad:false),
 Spec(name:"notice",text:"AVISO SINTÉTICO\nHorário de atendimento: 09:30 a 16:45\nCanal fictício: atendimento interno\nNão há dados pessoais reais\nRegistro sem efeito administrativo",font:"Helvetica",size:32,format:"pdf",bad:false),
 Spec(name:"negative",text:"DECLARAÇÃO DE TESTE\nO documento não atesta regularidade.\nO campo de aprovação está vazio.\nA ausência não significa reprovação.\nA análise depende de revisão humana.",font:"Helvetica",size:34,format:"png",bad:false),
 Spec(name:"blank",text:"",font:"Helvetica",size:34,format:"png",bad:true),
 Spec(name:"illegible",text:"ARQUIVO SINTÉTICO DE BAIXA RESOLUÇÃO\nConteúdo não utilizável para análise\nValor fictício: 918,26",font:"Helvetica",size:0.5,format:"png",bad:true),
 Spec(name:"partial",text:"ANEXO SINTÉTICO PARCIAL\nPrimeira página contém esta nota.\nSegunda página não contém texto.\nA cobertura deve ser conferida.",font:"Helvetica",size:34,format:"pdf",bad:true)
]
func render(_ text:String,_ font:String,_ size:CGFloat)->CGImage {
 let w=1700,h=1150
 let b=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:w,pixelsHigh:h,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
 NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:b)
 NSColor.white.setFill();NSRect(x:0,y:0,width:w,height:h).fill()
 let attrs:[NSAttributedString.Key:Any] = [.font:NSFont(name:font,size:size)!, .foregroundColor:NSColor.black]
 for (i,line) in text.components(separatedBy:"\n").enumerated(){(line as NSString).draw(at:NSPoint(x:90,y:990-i*95),withAttributes:attrs)}
 NSGraphicsContext.restoreGraphicsState();return b.cgImage!
}
func encode(_ img:CGImage,_ type:String)->Data {
 let data=NSMutableData();let d=CGImageDestinationCreateWithData(data,type as CFString,1,nil)!
 CGImageDestinationAddImage(d,img,[kCGImageDestinationLossyCompressionQuality:0.6] as CFDictionary);CGImageDestinationFinalize(d);return data as Data
}
func pdf(_ imgs:[CGImage])->Data {
 let data=NSMutableData();var bounds=CGRect(x:0,y:0,width:850,height:575)
 let c=CGContext(consumer:CGDataConsumer(data:data as CFMutableData)!,mediaBox:&bounds,nil)!
 for img in imgs{c.beginPDFPage(nil);c.draw(img,in:bounds);c.endPDFPage()};c.closePDF();return data as Data
}
let rows:[[String:Any]]=specs.map{s in
 let img=render(s.text,s.font,s.size)
 let data=s.format=="pdf" ? pdf(s.name=="partial" ? [img,render("",s.font,s.size)] : [img]) : encode(img,s.format=="jpg" ? "public.jpeg":"public.png")
 return ["file":"\(s.name).\(s.format)","expected_text":s.text,"expected_inconclusive":s.bad,"mime":s.format=="pdf" ? "application/pdf" : (s.format=="jpg" ? "image/jpeg":"image/png"),"bytes_base64":data.base64EncodedString(),"render_font":s.font,"font_size":s.size]
}
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:rows,options:[.sortedKeys]))
