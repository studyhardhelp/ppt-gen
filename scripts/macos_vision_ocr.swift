#!/usr/bin/env swift
import AppKit
import Foundation
import Vision

struct OCRLine: Codable {
    let text: String
    let x: Double
    let y: Double
    let w: Double
    let h: Double
    let confidence: Float
}

guard CommandLine.arguments.count >= 2 else {
    fputs("usage: macos_vision_ocr.swift IMAGE [LANGUAGE]\n", stderr)
    exit(2)
}
let imagePath = CommandLine.arguments[1]
let language = CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : "eng"
guard let image = NSImage(contentsOfFile: imagePath) else {
    fputs("cannot open image\n", stderr)
    exit(2)
}
var rect = NSRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else {
    fputs("cannot create CGImage\n", stderr)
    exit(2)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
let languageMap = ["eng": "en-US", "chi_sim": "zh-Hans", "chi_tra": "zh-Hant", "jpn": "ja-JP", "kor": "ko-KR"]
request.recognitionLanguages = language.split(separator: "+").compactMap { languageMap[String($0)] }
do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
    let width = Double(cgImage.width)
    let height = Double(cgImage.height)
    let lines = (request.results ?? []).compactMap { observation -> OCRLine? in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return OCRLine(
            text: candidate.string,
            x: box.minX * width,
            y: (1.0 - box.maxY) * height,
            w: box.width * width,
            h: box.height * height,
            confidence: candidate.confidence
        )
    }
    let data = try JSONEncoder().encode(lines)
    print(String(data: data, encoding: .utf8) ?? "[]")
} catch {
    fputs("\(error)\n", stderr)
    exit(1)
}
