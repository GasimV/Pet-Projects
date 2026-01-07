#include "qr_generator.hpp"
#include "qrcodegen.hpp"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <sstream>
#include <cstring>

using namespace qrcodegen;

std::string QRGenerator::generateSVG(const std::string& data, const json& design) {
    // Generate QR code
    QrCode qr = QrCode::encodeText(data.c_str(), QrCode::Ecc::MEDIUM);

    // Extract design parameters
    std::string primaryColor = design.value("primaryColor", "#000000");
    std::string backgroundColor = design.value("backgroundColor", "#FFFFFF");
    std::string pattern = design.value("pattern", "square");

    int size = qr.getSize();
    int border = 4;
    int totalSize = (size + border * 2) * 10;

    std::ostringstream svg;
    svg << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
    svg << "<svg xmlns=\"http://www.w3.org/2000/svg\" version=\"1.1\" viewBox=\"0 0 "
        << totalSize << " " << totalSize << "\" stroke=\"none\">\n";
    svg << "<rect width=\"100%\" height=\"100%\" fill=\"" << backgroundColor << "\"/>\n";

    for (int y = 0; y < size; y++) {
        for (int x = 0; x < size; x++) {
            if (qr.getModule(x, y)) {
                int px = (x + border) * 10;
                int py = (y + border) * 10;

                if (pattern == "rounded") {
                    svg << "<rect x=\"" << px << "\" y=\"" << py
                        << "\" width=\"10\" height=\"10\" rx=\"2\" fill=\"" << primaryColor << "\"/>\n";
                } else if (pattern == "dots") {
                    svg << "<circle cx=\"" << (px + 5) << "\" cy=\"" << (py + 5)
                        << "\" r=\"4\" fill=\"" << primaryColor << "\"/>\n";
                } else {
                    svg << "<rect x=\"" << px << "\" y=\"" << py
                        << "\" width=\"10\" height=\"10\" fill=\"" << primaryColor << "\"/>\n";
                }
            }
        }
    }

    svg << "</svg>\n";
    return svg.str();
}

std::vector<unsigned char> QRGenerator::generatePNG(const std::string& data, const json& design, int size) {
    // Generate QR code
    QrCode qr = QrCode::encodeText(data.c_str(), QrCode::Ecc::MEDIUM);

    std::string primaryColor = design.value("primaryColor", "#000000");
    std::string backgroundColor = design.value("backgroundColor", "#FFFFFF");

    // Parse hex colors
    auto parseHex = [](const std::string& hex) -> std::array<unsigned char, 3> {
        unsigned int r, g, b;
        sscanf(hex.c_str() + 1, "%02x%02x%02x", &r, &g, &b);
        return {(unsigned char)r, (unsigned char)g, (unsigned char)b};
    };

    auto fgColor = parseHex(primaryColor);
    auto bgColor = parseHex(backgroundColor);

    int qrSize = qr.getSize();
    int border = 4;
    int totalModules = qrSize + border * 2;
    int scale = size / totalModules;
    int actualSize = totalModules * scale;

    std::vector<unsigned char> pixels(actualSize * actualSize * 3);

    for (int y = 0; y < actualSize; y++) {
        for (int x = 0; x < actualSize; x++) {
            int moduleX = x / scale - border;
            int moduleY = y / scale - border;

            bool isBlack = moduleX >= 0 && moduleX < qrSize && moduleY >= 0 && moduleY < qrSize
                           && qr.getModule(moduleX, moduleY);

            auto& color = isBlack ? fgColor : bgColor;
            int idx = (y * actualSize + x) * 3;
            pixels[idx] = color[0];
            pixels[idx + 1] = color[1];
            pixels[idx + 2] = color[2];
        }
    }

    unsigned char* pngData = nullptr;
    int pngSize = 0;

    stbi_write_png_to_func([](void* context, void* data, int size) {
        auto* vec = (std::vector<unsigned char>*)context;
        unsigned char* bytes = (unsigned char*)data;
        vec->assign(bytes, bytes + size);
    }, &pixels, actualSize, actualSize, 3, pixels.data(), actualSize * 3);

    return pixels;
}

std::vector<unsigned char> QRGenerator::generateJPG(const std::string& data, const json& design, int size) {
    // Similar to PNG but use JPG encoding
    QrCode qr = QrCode::encodeText(data.c_str(), QrCode::Ecc::MEDIUM);

    std::string primaryColor = design.value("primaryColor", "#000000");
    std::string backgroundColor = design.value("backgroundColor", "#FFFFFF");

    auto parseHex = [](const std::string& hex) -> std::array<unsigned char, 3> {
        unsigned int r, g, b;
        sscanf(hex.c_str() + 1, "%02x%02x%02x", &r, &g, &b);
        return {(unsigned char)r, (unsigned char)g, (unsigned char)b};
    };

    auto fgColor = parseHex(primaryColor);
    auto bgColor = parseHex(backgroundColor);

    int qrSize = qr.getSize();
    int border = 4;
    int totalModules = qrSize + border * 2;
    int scale = size / totalModules;
    int actualSize = totalModules * scale;

    std::vector<unsigned char> pixels(actualSize * actualSize * 3);

    for (int y = 0; y < actualSize; y++) {
        for (int x = 0; x < actualSize; x++) {
            int moduleX = x / scale - border;
            int moduleY = y / scale - border;

            bool isBlack = moduleX >= 0 && moduleX < qrSize && moduleY >= 0 && moduleY < qrSize
                           && qr.getModule(moduleX, moduleY);

            auto& color = isBlack ? fgColor : bgColor;
            int idx = (y * actualSize + x) * 3;
            pixels[idx] = color[0];
            pixels[idx + 1] = color[1];
            pixels[idx + 2] = color[2];
        }
    }

    std::vector<unsigned char> jpgData;
    stbi_write_jpg_to_func([](void* context, void* data, int size) {
        auto* vec = (std::vector<unsigned char>*)context;
        unsigned char* bytes = (unsigned char*)data;
        vec->assign(bytes, bytes + size);
    }, &jpgData, actualSize, actualSize, 3, pixels.data(), 90);

    return jpgData;
}
