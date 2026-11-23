// Reproducible synthetic OCR evaluation artifacts, no user documents.
import Foundation
import AppKit
import PDFKit
import ImageIO
import CoreGraphics

let expected = "ELO TESTE SINTETICO\nCTR-1042 FOR-031\nTOTAL 12345"
func makeImage(blank: Bool = false, degraded: Bool = false, oversized: Bool = false, text: String = expected) -> CGImage {
    let width = oversized ? 4000 : 1200, height = oversized ? 4000 : 600
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8,
        samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    NSColor.white.setFill(); NSRect(x: 0, y: 0, width: width, height: height).fill()
    if !blank && !oversized {
        // Degraded fixture is deliberately unreadable: text is rendered below one-pixel character height.
        let size: CGFloat = degraded ? 0.5 : 48
        let attributes: [NSAttributedString.Key: Any] = [.font: NSFont.monospacedSystemFont(ofSize: size, weight: .regular), .foregroundColor: NSColor.black]
        for (index, line) in text.components(separatedBy: "\n").enumerated() {
            (line as NSString).draw(at: NSPoint(x: 70, y: 400 - index * 100), withAttributes: attributes)
        }
    }
    NSGraphicsContext.restoreGraphicsState()
    return bitmap.cgImage!
}
func encode(_ image: CGImage, type: CFString, orientation: Int = 1) -> Data {
    let output = NSMutableData()
    let destination = CGImageDestinationCreateWithData(output, type, 1, nil)!
    CGImageDestinationAddImage(destination, image, [kCGImageDestinationLossyCompressionQuality: 0.95, kCGImagePropertyOrientation: orientation] as CFDictionary)
    CGImageDestinationFinalize(destination)
    return output as Data
}
func pdf(_ image: CGImage, count: Int = 1) -> Data {
    let result = NSMutableData()
    let consumer = CGDataConsumer(data: result as CFMutableData)!
    var bounds = CGRect(x: 0, y: 0, width: 600, height: 300)
    let context = CGContext(consumer: consumer, mediaBox: &bounds, nil)!
    for _ in 0..<count { context.beginPDFPage(nil); context.draw(image, in: bounds); context.endPDFPage() }
    context.closePDF()
    return result as Data
}
func inverted(_ image: CGImage) -> CGImage {
    let context = CGContext(data: nil, width: image.width, height: image.height, bitsPerComponent: 8,
        bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    context.translateBy(x: CGFloat(image.width), y: CGFloat(image.height)); context.rotate(by: .pi)
    context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
    return context.makeImage()!
}
let image = makeImage()
let fixtures: [String: String] = ["png": encode(image, type: "public.png" as CFString).base64EncodedString(),
    "jpeg": encode(image, type: "public.jpeg" as CFString).base64EncodedString(),
    "portuguese": encode(makeImage(text: "AÇÃO DE REVISÃO\nCONTRATO SINTÉTICO\nFORNECEDOR FICTÍCIO"), type: "public.png" as CFString).base64EncodedString(),
    "jpeg_exif": encode(inverted(image), type: "public.jpeg" as CFString, orientation: 3).base64EncodedString(),
    "pdf": pdf(image).base64EncodedString(), "blank": encode(makeImage(blank: true), type: "public.png" as CFString).base64EncodedString(),
    "degraded": encode(makeImage(degraded: true), type: "public.png" as CFString).base64EncodedString(),
    "oversized": encode(makeImage(oversized: true), type: "public.png" as CFString).base64EncodedString(),
    "pdf_six_pages": pdf(image, count: 6).base64EncodedString()]
FileHandle.standardOutput.write(try JSONEncoder().encode(fixtures))
