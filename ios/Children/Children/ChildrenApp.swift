import SwiftUI

@main
struct ChildrenApp: App {
    @StateObject private var session = FamilySession()

    var body: some Scene {
        WindowGroup {
            Group {
                if session.isLoggedIn { HomeView() }
                else { LoginView() }
            }
            .environmentObject(session)
            .tint(Palette.clay)
        }
    }
}

enum Palette {
    static let clay = Color(red: 0.75, green: 0.39, blue: 0.28)
    static let ink = Color(red: 0.19, green: 0.26, blue: 0.28)
    static let paper = Color(red: 0.98, green: 0.97, blue: 0.94)
    static let peach = Color(red: 1, green: 0.92, blue: 0.86)
}
