#include <iostream>
#include <fstream>
#include <vector>
#include <windows.h>
#include <cstdint>

class BMPHandler {
private:
    std::string inputFile, outputFile;
    BITMAPFILEHEADER fileHeader;
    BITMAPINFOHEADER infoHeader;
    std::vector<std::vector<uint8_t>> pixelData;

public:
    BMPHandler(const std::string& input, const std::string& output) : inputFile(input), outputFile(output) {}
    
    bool loadBMP();
    void displayBMP() const;
    void drawCross();
    bool saveBMP() const;
};

bool BMPHandler::loadBMP() {
    std::ifstream file(inputFile, std::ios::binary);
    if (!file) {
        std::cerr << "Error: Cannot open file " << inputFile << "!\n";
        return false;
    }
    
    file.read(reinterpret_cast<char*>(&fileHeader), sizeof(BITMAPFILEHEADER));
    file.read(reinterpret_cast<char*>(&infoHeader), sizeof(BITMAPINFOHEADER));

    if (infoHeader.biBitCount != 24 && infoHeader.biBitCount != 32) {
        std::cerr << "Error: Only 24-bit and 32-bit BMP files are supported!\n";
        return false;
    }
    
    int width = infoHeader.biWidth;
    int height = std::abs(infoHeader.biHeight);
    int bytesPerPixel = infoHeader.biBitCount / 8;
    int rowPadding = (4 - (width * bytesPerPixel) % 4) % 4;
    
    pixelData.resize(height, std::vector<uint8_t>(width));
    
    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            uint8_t b, g, r;
            file.read(reinterpret_cast<char*>(&b), 1);
            file.read(reinterpret_cast<char*>(&g), 1);
            file.read(reinterpret_cast<char*>(&r), 1);
            
            pixelData[i][j] = (r == 255 && g == 255 && b == 255) ? ' ' : '#';
            if (bytesPerPixel == 4) file.ignore(1); // Ignore alpha channel if present
        }
        file.ignore(rowPadding);
    }
    file.close();
    return true;
}

void BMPHandler::displayBMP() const {
    for (const auto& row : pixelData) {
        for (char pixel : row) {
            std::cout << pixel << pixel; // Doubling for better aspect ratio
        }
        std::cout << '\n';
    }
}

void BMPHandler::drawCross() {
    int width = pixelData[0].size();
    int height = pixelData.size();
    for (int i = 0; i < height; i++) {
        pixelData[i][i] = '*';
        pixelData[i][width - 1 - i] = '*';
    }
}

bool BMPHandler::saveBMP() const {
    std::ofstream file(outputFile, std::ios::binary);
    if (!file) {
        std::cerr << "Error: Cannot create file " << outputFile << "!\n";
        return false;
    }
    
    file.write(reinterpret_cast<const char*>(&fileHeader), sizeof(BITMAPFILEHEADER));
    file.write(reinterpret_cast<const char*>(&infoHeader), sizeof(BITMAPINFOHEADER));

    int width = infoHeader.biWidth;
    int height = std::abs(infoHeader.biHeight);
    int bytesPerPixel = infoHeader.biBitCount / 8;
    int rowPadding = (4 - (width * bytesPerPixel) % 4) % 4;

    for (int i = 0; i < height; i++) {
        for (int j = 0; j < width; j++) {
            uint8_t color = (pixelData[i][j] == ' ') ? 255 : 0;
            file.put(static_cast<char>(color)).put(static_cast<char>(color)).put(static_cast<char>(color));
            if (bytesPerPixel == 4) file.put(0);
        }
        for (int p = 0; p < rowPadding; p++) file.put(0);
    }
    file.close();
    return true;
}

int main() {
    std::string inputFile, outputFile;
    std::cout << ">> Enter input BMP file name: ";
    std::cin >> inputFile;
    
    std::cout << ">> Enter output BMP file name: ";
    std::cin >> outputFile;
    
    BMPHandler bmp(inputFile, outputFile);
    if (!bmp.loadBMP()) return 1;
    
    std::cout << "Original Image:\n";
    bmp.displayBMP();
    
    bmp.drawCross();
    std::cout << "\nImage with Cross:\n";
    bmp.displayBMP();
    
    if (!bmp.saveBMP()) return 1;
    
    std::cout << "Image saved successfully as " << outputFile << "\n";
    return 0;
}