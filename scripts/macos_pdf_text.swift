#!/usr/bin/env swift
import Foundation
import PDFKit

guard CommandLine.arguments.count >= 2 else {
    fputs("usage: macos_pdf_text.swift FILE.pdf\n", stderr)
    exit(2)
}
guard let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    fputs("cannot open PDF\n", stderr)
    exit(2)
}
for index in 0..<document.pageCount {
    print("[Page \(index + 1)]")
    print(document.page(at: index)?.string ?? "")
    print("")
}
