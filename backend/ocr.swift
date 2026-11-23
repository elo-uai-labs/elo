// Bounded local rasterizer only; recognition is performed by local Tesseract.
import Foundation
import PDFKit
import ImageIO
import AppKit
import Darwin
let maximumInput = 1024 * 1024
let maximumPixels = 12_000_000
let maximumPages = 5
struct PageInfo: Codable { let page: Int; let width: Int; let height: Int }
enum Failure: Error { case input, pages, pixels, decoding, unsupported }

func process(_ data: Data, media: String) throws -> [PageInfo] {
    var pages: [PageInfo] = []
    func add(_ image: CGImage, page: Int) throws {
        guard image.width > 0 && image.height > 0 && image.width <= 12000 && image.height <= 12000 && image.width * image.height <= maximumPixels else { throw Failure.pixels }
        let output = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(output, "public.png" as CFString, 1, nil) else { throw Failure.decoding }
        CGImageDestinationAddImage(destination, image, nil)
        guard CGImageDestinationFinalize(destination), output.length <= 16 * 1024 * 1024 else { throw Failure.pixels }
        let file = URL(fileURLWithPath: CommandLine.arguments[2]).appendingPathComponent("page-\(page).png")
        try (output as Data).write(to: file, options: [.atomic])
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        pages.append(PageInfo(page: page, width: image.width, height: image.height))
    }
    if media == "application/pdf" {
        guard let document = PDFDocument(data: data), !document.isLocked && !document.isEncrypted else { throw Failure.decoding }
        guard (1...maximumPages).contains(document.pageCount) else { throw Failure.pages }
        for number in 0..<document.pageCount {
            try autoreleasepool {
                guard let page = document.page(at: number) else { throw Failure.decoding }
                let bounds = page.bounds(for: .cropBox)
                guard bounds.width.isFinite && bounds.height.isFinite && bounds.width > 0 && bounds.height > 0 && bounds.width <= 20000 && bounds.height <= 20000 else { throw Failure.pixels }
                let ratio = min(2048 / bounds.width, 2048 / bounds.height)
                let size = NSSize(width: max(1, floor(bounds.width * ratio)), height: max(1, floor(bounds.height * ratio)))
                let thumbnail = page.thumbnail(of: size, for: .cropBox)
                guard let image = thumbnail.cgImage(forProposedRect: nil, context: nil, hints: nil) else { throw Failure.decoding }
                try add(image, page: number + 1)
            }
        }
    } else if media == "image/png" || media == "image/jpeg" {
        guard let source = CGImageSourceCreateWithData(data as CFData, [kCGImageSourceShouldCache: false] as CFDictionary), CGImageSourceGetCount(source) == 1,
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = properties[kCGImagePropertyPixelWidth] as? Int,
              let height = properties[kCGImagePropertyPixelHeight] as? Int else { throw Failure.decoding }
        guard width > 0 && height > 0 && width <= 12000 && height <= 12000 && width * height <= maximumPixels else { throw Failure.pixels }
        guard let type = CGImageSourceGetType(source) as String?, type == (media == "image/png" ? "public.png" : "public.jpeg") else { throw Failure.unsupported }
        // ImageIO physically applies EXIF orientation, so TSV boxes match the displayed image.
        guard let image = CGImageSourceCreateThumbnailAtIndex(source, 0,
            [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true,
             kCGImageSourceThumbnailMaxPixelSize: max(width, height), kCGImageSourceShouldCache: false] as CFDictionary) else { throw Failure.decoding }
        try add(image, page: 1)
    } else { throw Failure.unsupported }
    return pages
}

// Enforced wall time lives in the Python caller; CPU also bounded here. macOS has no reliable RLIMIT_AS.
var cpuLimit = rlimit(rlim_cur: 25, rlim_max: 25)
_ = setrlimit(RLIMIT_CPU, &cpuLimit)
do {
    guard CommandLine.arguments.count == 3 else { throw Failure.input }
    let data = FileHandle.standardInput.readData(ofLength: maximumInput + 1)
    guard !data.isEmpty && data.count <= maximumInput else { throw Failure.input }
    let result = try process(data, media: CommandLine.arguments[1])
    FileHandle.standardOutput.write(try JSONEncoder().encode(result))
} catch {
    // No parser text, original content or local path is returned in diagnostics.
    exit(2)
}
