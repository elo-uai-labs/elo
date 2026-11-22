import Foundation
import FoundationModels

@Generable
struct Summary {
    @Guide(description: "Síntese em português do Brasil, com os identificadores das evidências citados junto às afirmações")
    var text: String

    @Guide(description: "Somente identificadores literais de registros que aparecem no texto e nas evidências de entrada")
    var sourceIDs: [String]
}

struct Input: Decodable {
    let instructions: String
    let evidence: String
}

struct Output: Encodable {
    let text: String
    let source_ids: [String]
    let model: String
}

@main
struct EloOnDevice {
    static func main() async throws {
        let input = try JSONDecoder().decode(Input.self, from: FileHandle.standardInput.readDataToEndOfFile())
        let session = LanguageModelSession(instructions: input.instructions)
        let response = try await session.respond(to: input.evidence, generating: Summary.self)
        let summary = response.content
        let model = "Apple Foundation Models on-device (\(ProcessInfo.processInfo.operatingSystemVersionString))"
        let result = Output(text: summary.text, source_ids: summary.sourceIDs, model: model)
        FileHandle.standardOutput.write(try JSONEncoder().encode(result))
    }
}
