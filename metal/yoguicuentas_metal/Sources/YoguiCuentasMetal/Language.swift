import Foundation
import Combine

/// Presentation preference only. Each launch starts in Spanish; no scenario mutation.
final class AppLanguage: ObservableObject {
    static let shared = AppLanguage()
    @Published var code = "es"
}

enum L10n {
    private static let pattern: NSRegularExpression = {
        let keys = english.keys.sorted { $0.count == $1.count ? $0 < $1 : $0.count > $1.count }
        let alternatives = keys.map { "(?<!\\w)" + NSRegularExpression.escapedPattern(for: $0) + "(?!\\w)" }
        return try! NSRegularExpression(pattern: alternatives.joined(separator: "|"))
    }()

    /// Translate display text, leaving model identifiers and stored values unchanged.
    static func text(_ source: String) -> String {
        guard AppLanguage.shared.code == "en" else { return source }
        if let translated = english[source] { return translated }
        let input = source as NSString
        let result = NSMutableString(string: source)
        let pathPattern = try! NSRegularExpression(pattern: #"https?://\S+|(?:/|~/)[^\s]+"#)
        let paths = pathPattern.matches(in: source, range: NSRange(location: 0, length: input.length))
        for match in pattern.matches(in: source, range: NSRange(location: 0, length: input.length)).reversed() {
            if paths.contains(where: { NSIntersectionRange($0.range, match.range).length > 0 }) { continue }
            let key = input.substring(with: match.range)
            result.replaceCharacters(in: match.range, with: english[key] ?? key)
        }
        return result as String
    }
}
