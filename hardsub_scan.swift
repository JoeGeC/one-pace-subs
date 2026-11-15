// hardsub_scan.swift — single-pass hardcoded-subtitle scanner (macOS, Vision).
// Driven by ocr_hardsubs.py, which compiles and runs it; not meant to be run by hand.
//
// Usage: hardsub_scan <video> <out.jsonl> [bandFrac=0.24] [scanEvery=12]
//
// Decodes every frame at 1280x720 and, in the bottom `bandFrac` of the frame,
// builds a coarse mask of "subtitle-like" pixels (near-white with a dark pixel
// close by = outlined text). Consecutive frames whose masks overlap belong to
// the same subtitle; a mask change marks a frame-exact boundary. OCR runs only
// on a couple of frames per subtitle (not every frame). Separately, every
// `scanEvery` frames the area above the band is OCR'd for captions/title cards.
// It also counts pink outlined pixels in the band per frame (OP karaoke lyrics),
// so the driver can find and drop the opening.
//
// Output JSONL records:
//   {"k":"meta","fps_num":..,"fps_den":..,"w":1280,"h":720,"band":..}
//   {"k":"seg","s":startFrame,"e":endFrameExclusive,"o":[{"f":frame,"t":text,"c":conf,"x":..,"y":..,"w":..,"h":..}, ...]}
//   {"k":"scan","f":frame,"o":[obs...]}            (coords normalised to the full frame, origin bottom-left)
//   {"k":"pink","f":[frames with OP-lyric colour]}
import AVFoundation
import CoreGraphics
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 3 else { FileHandle.standardError.write("usage: hardsub_scan video out.jsonl [band] [scanEvery]\n".data(using: .utf8)!); exit(2) }
let videoURL = URL(fileURLWithPath: args[1])
let outPath = args[2]
let bandFrac = args.count > 3 ? Double(args[3])! : 0.24
let scanEvery = args.count > 4 ? Int(args[4])! : 12

let W = 1280, H = 720
let bandY0 = Int(Double(H) * (1 - bandFrac))   // top row of band (image coords, origin top-left)
let bandH = H - bandY0
let CELL = 8
let cellsX = W / CELL, cellsY = (bandH + CELL - 1) / CELL

let asset = AVURLAsset(url: videoURL)
let sem = DispatchSemaphore(value: 0)
var vtrack: AVAssetTrack?
asset.loadTracks(withMediaType: .video) { t, _ in vtrack = t?.first; sem.signal() }
sem.wait()
guard let track = vtrack else { print("no video track"); exit(1) }
var fpsNum = 24000, fpsDen = 1001
if let fr = try? awaitValue({ try await track.load(.nominalFrameRate) }) {
    if abs(Double(fr) - 23.976) > 0.01 { fpsNum = Int((Double(fr) * 1000).rounded()); fpsDen = 1000 }
}
func awaitValue<T>(_ f: @escaping () async throws -> T) throws -> T {
    var r: Result<T, Error>!
    let s = DispatchSemaphore(value: 0)
    Task { do { r = .success(try await f()) } catch { r = .failure(error) }; s.signal() }
    s.wait(); return try r.get()
}

let reader = try! AVAssetReader(asset: asset)
let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
])
output.alwaysCopiesSampleData = false
reader.add(output)
reader.startReading()

// ---------- OCR (async, bounded concurrency) ----------
let ocrQueue = DispatchQueue(label: "ocr", attributes: .concurrent)
let ocrSlots = DispatchSemaphore(value: 8)
let group = DispatchGroup()
let lock = NSLock()
var segOCR: [Int: [[String: Any]]] = [:]       // segment start frame -> obs
var scanOCR: [Int: [[String: Any]]] = [:]      // frame -> obs

func makeImage(_ data: Data, width: Int, height: Int) -> CGImage? {
    let cs = CGColorSpaceCreateDeviceRGB()
    guard let prov = CGDataProvider(data: data as CFData) else { return nil }
    return CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: width * 4,
                   space: cs, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
                   provider: prov, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
}

/// OCR `data` (a W x rows BGRA crop whose top row is image row `row0`). Coordinates are mapped back to the full frame.
func ocr(_ data: Data, rows: Int, row0: Int, minHeight: Float, frame: Int, done: @escaping ([[String: Any]]) -> Void) {
    ocrSlots.wait(); group.enter()
    ocrQueue.async {
        defer { ocrSlots.signal(); group.leave() }
        autoreleasepool {
            guard let img = makeImage(data, width: W, height: rows) else { done([]); return }
            let req = VNRecognizeTextRequest()
            req.recognitionLevel = .accurate
            req.usesLanguageCorrection = true
            req.recognitionLanguages = ["en-US"]
            req.minimumTextHeight = minHeight
            try? VNImageRequestHandler(cgImage: img).perform([req])
            var obs: [[String: Any]] = []
            let fy0 = Double(H - row0 - rows) / Double(H), fh = Double(rows) / Double(H)
            for r in req.results ?? [] {
                guard let c = r.topCandidates(1).first else { continue }
                let b = r.boundingBox
                obs.append(["f": frame, "t": c.string, "c": Double(c.confidence),
                            "x": Double(b.minX), "y": fy0 + Double(b.minY) * fh, "w": Double(b.width), "h": Double(b.height) * fh])
            }
            done(obs)
        }
    }
}

// ---------- per-frame band analysis ----------
@inline(__always) func isWhite(_ p: UnsafePointer<UInt8>) -> Bool {
    let b = p[0], g = p[1], r = p[2]
    let mn = min(r, min(g, b)), mx = max(r, max(g, b))
    return mn > 185 && mx - mn < 45
}
@inline(__always) func isPink(_ p: UnsafePointer<UInt8>) -> Bool {
    let b = Int(p[0]), g = Int(p[1]), r = Int(p[2])
    return r > 190 && b > 130 && g < r - 55 && g < b - 10
}
@inline(__always) func isDark(_ p: UnsafePointer<UInt8>) -> Bool {
    return max(p[0], max(p[1], p[2])) < 100
}

var pinkFrames: [Int] = []
var curStart = -1, curAge = 0
var prevCells = [Bool](repeating: false, count: cellsX * cellsY)
var segs: [(Int, Int)] = []
var frame = 0
let OFF = 3  // outline search distance (px at 720p)

while let sb = output.copyNextSampleBuffer() {
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    CVPixelBufferLockBaseAddress(pb, .readOnly)
    let base = CVPixelBufferGetBaseAddress(pb)!.assumingMemoryBound(to: UInt8.self)
    let bpr = CVPixelBufferGetBytesPerRow(pb)

    var cells = [Bool](repeating: false, count: cellsX * cellsY)
    var cellCount = [UInt16](repeating: 0, count: cellsX * cellsY)
    var white = 0, pink = 0
    var y = bandY0 + OFF
    while y < H - OFF {
        let row = base + y * bpr
        var x = OFF
        while x < W - OFF {
            let p = UnsafePointer(row + x * 4)
            let w = isWhite(p), pk = !w && isPink(p)
            if w || pk {
                let near = isDark(p - OFF * 4) || isDark(p + OFF * 4) || isDark(p - OFF * bpr) || isDark(p + OFF * bpr)
                if near {
                    if w {
                        white += 1
                        let ci = ((y - bandY0) / CELL) * cellsX + x / CELL
                        cellCount[ci] &+= 1
                    } else { pink += 1 }
                }
            }
            x += 2
        }
        y += 2
    }
    for i in 0..<cells.count { cells[i] = cellCount[i] >= 2 }
    if pink > 60 { pinkFrames.append(frame) }

    let present = white > 60
    var inter = 0, uni = 0
    for i in 0..<cells.count { if cells[i] || prevCells[i] { uni += 1; if cells[i] && prevCells[i] { inter += 1 } } }
    let iou = uni == 0 ? 1.0 : Double(inter) / Double(uni)

    if curStart >= 0 && (!present || iou < 0.45) {
        segs.append((curStart, frame)); curStart = -1
    }
    if present && curStart < 0 { curStart = frame; curAge = 0 }

    // OCR a few frames per segment: shortly after it appears (past a fade-in) and ~1s in.
    if curStart >= 0 {
        if curAge == 3 || curAge == 24 {
            var d = Data(count: W * bandH * 4)
            d.withUnsafeMutableBytes { dst in
                let dp = dst.baseAddress!.assumingMemoryBound(to: UInt8.self)
                for r in 0..<bandH { memcpy(dp + r * W * 4, base + (bandY0 + r) * bpr, W * 4) }
            }
            let key = curStart
            ocr(d, rows: bandH, row0: bandY0, minHeight: 0.12, frame: frame) { obs in
                lock.lock(); segOCR[key, default: []].append(contentsOf: obs); lock.unlock()
            }
        }
        curAge += 1
    }
    // Caption scan above the band.
    if frame % scanEvery == 0 {
        var d = Data(count: W * bandY0 * 4)
        d.withUnsafeMutableBytes { dst in
            let dp = dst.baseAddress!.assumingMemoryBound(to: UInt8.self)
            for r in 0..<bandY0 { memcpy(dp + r * W * 4, base + r * bpr, W * 4) }
        }
        let f = frame
        ocr(d, rows: bandY0, row0: 0, minHeight: 0.03, frame: f) { obs in
            lock.lock(); scanOCR[f] = obs; lock.unlock()
        }
    }
    prevCells = cells
    CVPixelBufferUnlockBaseAddress(pb, .readOnly)
    frame += 1
    if frame % 5000 == 0 { FileHandle.standardError.write("  frame \(frame)\n".data(using: .utf8)!) }
}
if curStart >= 0 { segs.append((curStart, frame)) }
group.wait()

var lines: [String] = []
func j(_ o: Any) -> String { String(data: try! JSONSerialization.data(withJSONObject: o), encoding: .utf8)! }
lines.append(j(["k": "meta", "fps_num": fpsNum, "fps_den": fpsDen, "w": W, "h": H, "band": bandFrac, "frames": frame]))
for (s, e) in segs { lines.append(j(["k": "seg", "s": s, "e": e, "o": segOCR[s] ?? []])) }
for f in scanOCR.keys.sorted() where !(scanOCR[f]!.isEmpty) { lines.append(j(["k": "scan", "f": f, "o": scanOCR[f]!])) }
lines.append(j(["k": "pink", "f": pinkFrames]))
try! lines.joined(separator: "\n").write(toFile: outPath, atomically: true, encoding: .utf8)
FileHandle.standardError.write("  \(frame) frames, \(segs.count) segments\n".data(using: .utf8)!)
