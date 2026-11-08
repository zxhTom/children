import SwiftUI
import WebKit
import AVFAudio

struct LoginView: View {
    @EnvironmentObject private var session: FamilySession
    @State private var username = ""
    @State private var password = ""

    var body: some View {
        ZStack {
            Palette.paper.ignoresSafeArea()
            Circle().fill(Palette.peach.opacity(0.75)).frame(width: 340, height: 340).blur(radius: 40).offset(x: 145, y: -300)
            VStack(alignment: .leading, spacing: 22) {
                Spacer()
                Text("✳").font(.system(size: 54)).foregroundStyle(Palette.clay)
                Text("家庭时光机").font(.system(size: 36, weight: .bold, design: .serif)).foregroundStyle(Palette.ink)
                Text("把每一天的小事，留给长大的他们。").font(.subheadline).foregroundStyle(.secondary)
                VStack(spacing: 14) {
                    TextField("用户名", text: $username).textContentType(.username).textInputAutocapitalization(.never)
                    SecureField("密码", text: $password).textContentType(.password)
                }
                .padding(18).background(.white, in: RoundedRectangle(cornerRadius: 20))
                if let error = session.error { Text(error).font(.footnote).foregroundStyle(.red) }
                Button { Task { await session.login(username: username, password: password) } } label: {
                    HStack { Spacer(); Text(session.working ? "正在登录…" : "进入成长手册"); Image(systemName: "arrow.right"); Spacer() }
                        .font(.headline).padding(18)
                }
                .buttonStyle(.plain).foregroundStyle(.white).background(Palette.clay, in: RoundedRectangle(cornerRadius: 16))
                .disabled(username.isEmpty || password.isEmpty || session.working)
                Spacer()
                Text("仅家人可见 · 记录会同步到你的家庭手册").font(.caption).foregroundStyle(.secondary)
            }.padding(28)
        }
    }
}

struct HomeView: View {
    @EnvironmentObject private var session: FamilySession
    var body: some View {
        TabView {
            CareView().tabItem { Label("照护", systemImage: "heart.text.square") }
            FamilyWebView().tabItem { Label("成长手册", systemImage: "book.closed") }
            SettingsView().tabItem { Label("我的", systemImage: "person.crop.circle") }
        }
        .tint(Palette.clay)
    }
}

struct SettingsView: View {
    @EnvironmentObject private var session: FamilySession
    var body: some View {
        NavigationView {
            List {
                Section("宝宝档案") {
                    ForEach(session.children) { child in
                        HStack { Text("✳").foregroundStyle(Palette.clay); Text(child.displayName); Spacer(); if child.id == session.selectedChild?.id { Image(systemName: "checkmark").foregroundStyle(Palette.clay) } }
                            .contentShape(Rectangle()).onTapGesture { session.selectedChild = child }
                    }
                }
                Section { Button("退出登录", role: .destructive) { Task { await session.logout() } } }
            }
            .navigationTitle("我的家庭")
        }.navigationViewStyle(.stack)
    }
}

struct FamilyWebView: UIViewRepresentable {
    func makeUIView(context: Context) -> WKWebView {
        let web = WKWebView(frame: .zero)
        web.scrollView.contentInsetAdjustmentBehavior = .always
        let cookies = HTTPCookieStorage.shared.cookies(for: URL(string: "https://children.port.toms.chat")!) ?? []
        Task {
            for cookie in cookies { await web.configuration.websiteDataStore.httpCookieStore.setCookie(cookie) }
            web.load(URLRequest(url: URL(string: "https://children.port.toms.chat/")!))
        }
        return web
    }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}

struct CareView: View {
    @EnvironmentObject private var session: FamilySession
    @State private var day = Date()
    @State private var events: [CareEvent] = []
    @State private var editor = false
    @State private var editing: CareEvent?
    @State private var error: String?
    private let kinds = [("feeding", "吃奶", "🍼"), ("poop", "臭臭", "💩"), ("pee", "尿尿", "💧"), ("sleep", "睡觉", "☾"), ("wake", "醒了", "☀"), ("other", "其他", "✦")]

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("每一件小事，都有意义").font(.system(size: 27, weight: .bold, design: .serif)).foregroundStyle(Palette.ink)
                        Text("吃奶、尿布和睡眠，按时间慢慢记下来。").font(.subheadline).foregroundStyle(.secondary)
                    }.padding(.top, 12)
                    if !session.children.isEmpty {
                        HStack(spacing: 10) {
                            ForEach(session.children) { child in
                                Button(child.displayName) { session.selectedChild = child; Task { await load() } }
                                    .font(.subheadline.weight(.semibold)).padding(.horizontal, 18).padding(.vertical, 10)
                                    .foregroundStyle(session.selectedChild?.id == child.id ? .white : Palette.ink)
                                    .background(session.selectedChild?.id == child.id ? Palette.clay : .white, in: Capsule())
                            }
                        }
                    }
                    HStack {
                        Button { day = Calendar.current.date(byAdding: .day, value: -1, to: day)!; Task { await load() } } label: { Image(systemName: "chevron.left") }
                        Spacer()
                        DatePicker("", selection: $day, displayedComponents: .date).labelsHidden().datePickerStyle(.compact)
                        Spacer()
                        Button { day = Calendar.current.date(byAdding: .day, value: 1, to: day)!; Task { await load() } } label: { Image(systemName: "chevron.right") }
                    }.padding(16).background(.white, in: RoundedRectangle(cornerRadius: 17))
                    HStack(spacing: 10) {
                        summary("今日记录", events.count, "square.stack")
                        summary("吃奶", events.filter { $0.kind == "feeding" }.count, "drop")
                        summary("臭臭", events.filter { $0.kind == "poop" }.count, "circle.grid.2x2")
                    }
                    Button { editing = nil; editor = true } label: {
                        Label("记一件小事", systemImage: "plus.circle.fill").font(.headline).frame(maxWidth: .infinity).padding(18)
                    }
                    .buttonStyle(.plain).foregroundStyle(.white).background(Palette.clay, in: RoundedRectangle(cornerRadius: 17))
                    HStack { Text("当天时间线").font(.title3.weight(.bold)); Spacer(); Text("\(events.count) 条").font(.caption).foregroundStyle(.secondary) }
                    if events.isEmpty {
                        VStack(spacing: 9) { Image(systemName: "heart.text.square").font(.largeTitle); Text("今天还没有记录"); Text("点击上方按钮，记下第一件小事").font(.caption) }
                            .foregroundStyle(.secondary).frame(maxWidth: .infinity).padding(.vertical, 54).background(.white, in: RoundedRectangle(cornerRadius: 18))
                    }
                    ForEach(events) { event in
                        Button { editing = event; editor = true } label: {
                            HStack(spacing: 13) {
                                Text(kinds.first { $0.0 == event.kind }?.2 ?? "✦").font(.title2).frame(width: 48, height: 48).background(Palette.peach, in: RoundedRectangle(cornerRadius: 14))
                                VStack(alignment: .leading, spacing: 5) {
                                    Text((kinds.first { $0.0 == event.kind }?.1 ?? "其他") + (event.amount_ml.map { " · \($0) ml" } ?? "")).font(.subheadline.weight(.bold)).foregroundStyle(Palette.ink)
                                    if let note = event.note, !note.isEmpty { Text(note).font(.caption).foregroundStyle(.secondary).lineLimit(2) }
                                }
                                Spacer()
                                Text(String(event.occurred_at.dropFirst(11).prefix(5))).font(.subheadline.weight(.bold)).monospacedDigit().foregroundStyle(Palette.clay)
                            }.padding(14).background(.white, in: RoundedRectangle(cornerRadius: 17))
                        }.buttonStyle(.plain)
                    }
                    if let error { Text(error).font(.footnote).foregroundStyle(.red) }
                }.padding(18)
            }
            .background(Palette.paper)
            .navigationTitle("日常照护").navigationBarTitleDisplayMode(.inline)
            .toolbar { Button("今天") { day = Date(); Task { await load() } } }
            .sheet(isPresented: $editor, onDismiss: { Task { await load() } }) { CareEditor(event: editing, day: day) }
            .onAppear { Task { await load() } }
            .onChange(of: session.selectedChild?.id) { _ in Task { await load() } }
            .onChange(of: day) { _ in Task { await load() } }
        }.navigationViewStyle(.stack)
    }

    private func summary(_ title: String, _ count: Int, _ icon: String) -> some View {
        VStack(alignment: .leading, spacing: 10) { Image(systemName: icon).foregroundStyle(Palette.clay); Text("\(count)").font(.title2.weight(.bold)).foregroundStyle(Palette.ink); Text(title).font(.caption).foregroundStyle(.secondary) }
            .frame(maxWidth: .infinity, alignment: .leading).padding(14).background(.white, in: RoundedRectangle(cornerRadius: 16))
    }

    private func load() async {
        guard let child = session.selectedChild else { return }
        do { events = try await session.get("/api/care?child_id=\(child.id)&day=\(localDateTime(day).prefix(10))"); error = nil }
        catch { self.error = error.localizedDescription }
    }
}
