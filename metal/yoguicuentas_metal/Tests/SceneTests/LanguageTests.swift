import XCTest
@testable import YoguiCuentasMetal

final class LanguageTests: XCTestCase {
    override func tearDown() {
        AppLanguage.shared.code = "es"
        super.tearDown()
    }
    func testSpanishDefaultAndBritishEnglish() {
        XCTAssertEqual(AppLanguage.shared.code, "es")
        XCTAssertEqual(L10n.text("Iniciar"), "Iniciar")
        AppLanguage.shared.code = "en"
        XCTAssertEqual(L10n.text("Iniciar"), "Start")
        XCTAssertEqual(L10n.text("Barra de colores"), "Colour bar")
        XCTAssertEqual(L10n.text("En ejecución · paso 128"), "Running · step 128")
        XCTAssertEqual(L10n.text("Campo guardado: /tmp/Material/Fuentes.csv"), "Field saved: /tmp/Material/Fuentes.csv")
    }
    func testLanguageChangesDoNotMutateScenarioOrCanonicalChoices() throws {
        let scenario = Scenario()
        let before = try JSONEncoder().encode(scenario)
        AppLanguage.shared.code = "en"
        XCTAssertEqual(L10n.text("Armónica"), "Harmonic")
        XCTAssertEqual(scenario.interface_mean, "Armónica")
        let after = try JSONEncoder().encode(scenario)
        let lhs = try JSONSerialization.jsonObject(with: before) as! NSDictionary
        let rhs = try JSONSerialization.jsonObject(with: after) as! NSDictionary
        XCTAssertEqual(lhs, rhs)
        AppLanguage.shared.code = "es"
        XCTAssertEqual(L10n.text("Armónica"), "Armónica")
    }
}
