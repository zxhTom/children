import SwiftUI
import AVFAudio
import Speech

@MainActor final class VoiceRecorder: ObservableObject {
    @Published var recording = false
    private var recorder: AVAudioRecorder?
    private var url: URL?

    func start() async throws {
        let permitted: Bool = await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { continuation.resume(returning: $0) }
        }
        guard permitted else {
            throw NSError(domain: "Voice", code: 1, userInfo: [NSLocalizedDescriptionKey: "请在系统设置中允许使用麦克风"])
        }
        try AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker])
        try AVAudioSession.sharedInstance().setActive(true)
        let path = FileManager.default.temporaryDirectory.appendingPathComponent("care-\(UUID().uuidString).m4a")
        let settings: [String: Any] = [AVFormatIDKey: Int(kAudioFormatMPEG4AAC), AVSampleRateKey: 16000, AVNumberOfChannelsKey: 1, AVEncoderBitRateKey: 64000]
        let recorder = try AVAudioRecorder(url: path, settings: settings)
        guard recorder.record() else { throw NSError(domain: "Voice", code: 2, userInfo: [NSLocalizedDescriptionKey: "录音启动失败"]) }
        self.recorder = recorder; self.url = path; recording = true
    }

    func stop() -> URL? {
        recorder?.stop(); recorder = nil; recording = false
        try? AVAudioSession.sharedInstance().setActive(false)
        return url
    }
}

struct CareEditor: View {
    @EnvironmentObject private var session: FamilySession
    @Environment(\.dismiss) private var dismiss
    @StateObject private var voice = VoiceRecorder()
    @State private var kind: String
    @State private var time: Date
    @State private var amount = ""
    @State private var note: String
    @State private var transcript = ""
    @State private var busy = false
    @State private var error: String?
    let event: CareEvent?
    private let kinds = [("feeding", "吃奶", "🍼"), ("poop", "臭臭", "💩"), ("pee", "尿尿", "💧"), ("sleep", "睡觉", "☾"), ("wake", "醒了", "☀"), ("other", "其他", "✦")]

    init(event: CareEvent?, day: Date) {
        self.event = event
        _kind = State(initialValue: event?.kind ?? "feeding")
        _time = State(initialValue: event.map { parseDateTime($0.occurred_at) } ?? (Calendar.current.isDateInToday(day) ? Date() : day))
        _amount = State(initialValue: event?.amount_ml.map(String.init) ?? "")
        _note = State(initialValue: event?.note ?? "")
    }

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("给这一天留个小记号").font(.system(size: 24, weight: .bold, design: .serif)).foregroundStyle(Palette.ink)
                    Text("选择宝宝和类型，时间可改到准确的分钟。").font(.subheadline).foregroundStyle(.secondary)
                    if session.children.count > 1 {
                        Picker("宝宝", selection: Binding(get: { session.selectedChild?.id ?? 0 }, set: { id in session.selectedChild = session.children.first { $0.id == id } })) {
                            ForEach(session.children) { Text($0.displayName).tag($0.id) }
                        }.padding(12).background(.white, in: RoundedRectangle(cornerRadius: 14))
                    }
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 9), count: 3), spacing: 9) {
                        ForEach(0..<kinds.count, id: \.self) { index in
                            let item = kinds[index]
                            Button { kind = item.0 } label: {
                                VStack(spacing: 5) { Text(item.2).font(.title2); Text(item.1).font(.caption.weight(.semibold)) }
                                    .frame(maxWidth: .infinity).frame(height: 70)
                                    .background(kind == item.0 ? Palette.peach : .white, in: RoundedRectangle(cornerRadius: 15))
                                    .overlay(RoundedRectangle(cornerRadius: 15).stroke(kind == item.0 ? Palette.clay : .clear))
                            }.buttonStyle(.plain)
                        }
                    }
                    VStack(alignment: .leading, spacing: 12) {
                        DatePicker("发生时间", selection: $time, displayedComponents: [.date, .hourAndMinute])
                        if kind == "feeding" {
                            HStack { Text("奶量"); Spacer(); TextField("选填", text: $amount).keyboardType(.numberPad).multilineTextAlignment(.trailing).frame(width: 80); Text("ml").foregroundStyle(.secondary) }
                        }
                    }.padding(17).background(.white, in: RoundedRectangle(cornerRadius: 16))
                    VStack(alignment: .leading, spacing: 9) {
                        Text("补充说明").font(.subheadline.weight(.semibold))
                        TextEditor(text: $note).frame(height: 85)
                    }.padding(17).background(.white, in: RoundedRectangle(cornerRadius: 16))
                    VStack(alignment: .leading, spacing: 10) {
                        Button { Task { await toggleRecording() } } label: {
                            Label(voice.recording ? "结束录音并识别" : "语音录入", systemImage: voice.recording ? "stop.circle.fill" : "mic.circle.fill")
                                .font(.headline).frame(maxWidth: .infinity).padding(15)
                        }
                        .buttonStyle(.plain).foregroundStyle(Palette.clay).background(Palette.peach, in: RoundedRectangle(cornerRadius: 14))
                        Text("说“下午三点半吃奶 120 毫升”。识别后请核对再保存。")
                            .font(.caption).foregroundStyle(.secondary)
                        if !transcript.isEmpty {
                            Text("识别文字").font(.caption.weight(.bold))
                            TextEditor(text: $transcript).frame(height: 85).padding(8).background(.white, in: RoundedRectangle(cornerRadius: 10))
                            Button("根据文字填写") { applyTranscript() }.font(.subheadline.weight(.semibold))
                        }
                    }
                    if let error { Text(error).font(.footnote).foregroundStyle(.red) }
                    Button { Task { await save() } } label: {
                        Text(busy ? "正在处理…" : "保存记录").font(.headline).frame(maxWidth: .infinity).padding(17)
                    }.buttonStyle(.plain).foregroundStyle(.white).background(Palette.clay, in: RoundedRectangle(cornerRadius: 16)).disabled(busy)
                }.padding(20)
            }
            .background(Palette.paper)
            .navigationTitle(event == nil ? "添加照护记录" : "修改照护记录").navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button("完成") { dismiss() } } }
        }.navigationViewStyle(.stack)
    }

    private func toggleRecording() async {
        if voice.recording {
            guard let file = voice.stop() else { return }
            busy = true; error = nil
            defer { busy = false; try? FileManager.default.removeItem(at: file) }
            do { transcript = try await session.transcribe(file) }
            catch {
                do { transcript = try await recognizeWithApple(file); self.error = "已使用 iPhone 语音识别，请特别核对时间和奶量。" }
                catch { self.error = "语音识别未完成：\(error.localizedDescription)" }
            }
        } else {
            do { try await voice.start() }
            catch { self.error = error.localizedDescription }
        }
    }

    private func recognizeWithApple(_ file: URL) async throws -> String {
        let status: SFSpeechRecognizerAuthorizationStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0) }
        }
        guard status == .authorized else {
            throw NSError(domain: "Speech", code: 1, userInfo: [NSLocalizedDescriptionKey: "请允许语音识别权限"])
        }
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "zh_CN")), recognizer.isAvailable else {
            throw NSError(domain: "Speech", code: 2, userInfo: [NSLocalizedDescriptionKey: "当前无法使用中文语音识别"])
        }
        let request = SFSpeechURLRecognitionRequest(url: file)
        request.contextualStrings = ["吃奶", "喂奶", "母乳", "配方奶", "便便", "臭臭", "尿尿", "换尿布", "睡觉", "醒了"]
        request.shouldReportPartialResults = false
        return try await withCheckedThrowingContinuation { continuation in
            var finished = false
            _ = recognizer.recognitionTask(with: request) { result, error in
                guard !finished else { return }
                if let result, result.isFinal {
                    finished = true; continuation.resume(returning: result.bestTranscription.formattedString)
                } else if let error {
                    finished = true; continuation.resume(throwing: error)
                }
            }
        }
    }

    private func applyTranscript() {
        let text = transcript
        if text.contains("便便") || text.contains("臭臭") || text.contains("大便") { kind = "poop" }
        else if text.contains("尿尿") || text.contains("小便") { kind = "pee" }
        else if text.contains("醒了") { kind = "wake" }
        else if text.contains("睡觉") || text.contains("睡着") { kind = "sleep" }
        else if text.contains("奶") { kind = "feeding" }
        else { kind = "other" }
        if let match = text.range(of: #"[\d零一二两三四五六七八九十百]{1,7}\s*(毫升|ml|mL)"#, options: .regularExpression) {
            let raw = String(text[match].prefix { $0.isNumber || "零一二两三四五六七八九十百".contains($0) })
            amount = String(spokenNumber(raw))
        }
        if let match = text.range(of: #"(凌晨|早上|上午|中午|下午|傍晚|晚上|夜里)?\s*[\d零一二两三四五六七八九十]{1,3}(点|:|：|时)(半|[\d零一二两三四五六七八九十]{1,3}分?)?"#, options: .regularExpression) {
            let spoken = String(text[match])
            let numbers = spoken.split(whereSeparator: { !$0.isNumber && !"零一二两三四五六七八九十".contains($0) }).map { spokenNumber(String($0)) }
            if let first = numbers.first {
                var hour = first
                if ["下午", "傍晚", "晚上", "夜里"].contains(where: spoken.contains) && hour < 12 { hour += 12 }
                if ["凌晨", "早上", "上午"].contains(where: spoken.contains) && hour == 12 { hour = 0 }
                let minute = spoken.contains("半") ? 30 : (numbers.dropFirst().first ?? 0)
                if hour < 24 && minute < 60, let changed = Calendar.current.date(bySettingHour: hour, minute: minute, second: 0, of: time) { time = changed }
            }
        }
        note = text
    }

    private func spokenNumber(_ text: String) -> Int {
        if let value = Int(text) { return value }
        let digits: [Character: Int] = ["零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9]
        var total = 0; var current = 0
        for char in text {
            if char == "百" || char == "十" { total += (current == 0 ? 1 : current) * (char == "百" ? 100 : 10); current = 0 }
            else if let value = digits[char] { current = current * 10 + value }
        }
        return total + current
    }

    private func save() async {
        guard let child = session.selectedChild else { error = "请选择宝宝"; return }
        let ml = Int(amount)
        if kind == "feeding" && !amount.isEmpty && (ml == nil || ml! < 1 || ml! > 2000) { error = "奶量请填写 1～2000 ml"; return }
        busy = true; error = nil
        defer { busy = false }
        let payload = CarePayload(child_id: child.id, kind: kind, occurred_at: localDateTime(time), amount_ml: kind == "feeding" ? ml : nil, note: note.isEmpty ? nil : note)
        do {
            let _: CareEvent = try await session.send(event.map { "/api/care/\($0.id)" } ?? "/api/care", method: event == nil ? "POST" : "PATCH", body: payload)
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}
