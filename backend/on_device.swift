import Foundation
import FoundationModels

@Generable
struct Claim {
    @Guide(description: "Uma afirmação factual curta em português apoiada somente nas fontes recebidas")
    var text: String
    @Guide(description: "IDs literais de registros recebidos que sustentam esta afirmação; serão mostrados ao lado do texto")
    var sourceIDs: [String]
}

@Generable
struct Summary {
    @Guide(description: "Afirmações factuais curtas com fontes individuais; siga a quantidade solicitada, podendo ser vazio quando não houver suporte nas fontes")
    var claims: [Claim]
    @Guide(description: "Limitação curta: o vínculo isolado não comprova irregularidade; sem novos fatos")
    var limitations: String
    @Guide(description: "Próxima verificação humana sugerida, sem decidir ou atribuir culpa")
    var suggestion: String
}

struct Input: Decodable {
    let instructions: String
    let evidence: String
}

struct OutputClaim: Encodable {
    let text: String
    let source_ids: [String]
}

struct Output: Encodable {
    let claims: [OutputClaim]
    let limitations: String
    let suggestion: String
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
        let result = Output(claims: summary.claims.map { OutputClaim(text: $0.text, source_ids: $0.sourceIDs) },
                            limitations: summary.limitations, suggestion: summary.suggestion, model: model)
        FileHandle.standardOutput.write(try JSONEncoder().encode(result))
    }
}
