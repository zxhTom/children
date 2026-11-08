import Foundation
import SwiftUI
import WebKit

private let baseURL = URL(string: "https://children.port.toms.chat")!
private func endpoint(_ path: String) -> URL { URL(string: path, relativeTo: baseURL)!.absoluteURL }

struct Child: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let nickname: String?
    let birth_date: String
    var displayName: String { nickname?.isEmpty == false ? nickname! : name }
}

struct CareEvent: Codable, Identifiable {
    let id: Int
    let child_id: Int
    let kind: String
    let occurred_at: String
    let amount_ml: Int?
    let note: String?
    let created_at: String
}

struct CarePayload: Encodable {
    let child_id: Int
    let kind: String
    let occurred_at: String
    let amount_ml: Int?
    let note: String?
}

struct Transcript: Decodable { let text: String }
struct APIError: Decodable { let detail: String }

@MainActor final class FamilySession: ObservableObject {
    @Published var isLoggedIn = false
    @Published var children: [Child] = []
    @Published var selectedChild: Child?
    @Published var error: String?
    @Published var working = false

    init() { Task { await restore() } }

    func restore() async {
        do { try await loadChildren(); isLoggedIn = true }
        catch { isLoggedIn = false }
    }

    func login(username: String, password: String) async {
        working = true; error = nil
        defer { working = false }
        do {
            var request = URLRequest(url: endpoint("/api/login"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["username": username, "password": password, "remember_me": true])
            let (_, response) = try await URLSession.shared.data(for: request)
            try check(response)
            try await loadChildren()
            isLoggedIn = true
        } catch { self.error = error.localizedDescription }
    }

    func logout() async {
        var request = URLRequest(url: endpoint("/api/logout"))
        request.httpMethod = "POST"
        _ = try? await URLSession.shared.data(for: request)
        for cookie in HTTPCookieStorage.shared.cookies ?? [] { HTTPCookieStorage.shared.deleteCookie(cookie) }
        let webCookies = WKWebsiteDataStore.default().httpCookieStore
        for cookie in await webCookies.allCookies() { await webCookies.delete(cookie) }
        children = []; selectedChild = nil; isLoggedIn = false
    }

    func loadChildren() async throws {
        children = try await get("/api/children")
        if let selectedChild { self.selectedChild = children.first(where: { $0.id == selectedChild.id }) ?? children.first }
        else { selectedChild = children.first }
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        let (data, response) = try await URLSession.shared.data(from: endpoint(path))
        try check(response, data: data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func send<T: Decodable, B: Encodable>(_ path: String, method: String, body: B) async throws -> T {
        var request = URLRequest(url: endpoint(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await URLSession.shared.data(for: request)
        try check(response, data: data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func transcribe(_ file: URL) async throws -> String {
        let boundary = UUID().uuidString
        var request = URLRequest(url: endpoint("/api/care/transcribe"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"file\"; filename=\"care.m4a\"\r\nContent-Type: audio/mp4\r\n\r\n".utf8)
        body.append(try Data(contentsOf: file))
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))
        request.httpBody = body
        let (data, response) = try await URLSession.shared.data(for: request)
        try check(response, data: data)
        return try JSONDecoder().decode(Transcript.self, from: data).text
    }

    private func check(_ response: URLResponse, data: Data = Data()) throws {
        guard let response = response as? HTTPURLResponse else { throw NSError(domain: "Family", code: 0, userInfo: [NSLocalizedDescriptionKey: "网络响应无效"]) }
        guard (200..<300).contains(response.statusCode) else {
            let message = (try? JSONDecoder().decode(APIError.self, from: data).detail) ?? "请求失败（\(response.statusCode)）"
            throw NSError(domain: "Family", code: response.statusCode, userInfo: [NSLocalizedDescriptionKey: message])
        }
    }
}

func localDateTime(_ date: Date) -> String {
    let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd'T'HH:mm"; formatter.locale = Locale(identifier: "zh_CN")
    return formatter.string(from: date)
}

func parseDateTime(_ text: String) -> Date {
    let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"; formatter.locale = Locale(identifier: "zh_CN")
    return formatter.date(from: text) ?? Date()
}
