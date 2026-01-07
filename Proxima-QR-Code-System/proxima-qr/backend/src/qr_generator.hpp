#pragma once
#include <string>
#include <vector>
#include "nlohmann/json.hpp"

using json = nlohmann::json;

class QRGenerator {
public:
    std::string generateSVG(const std::string& data, const json& design);
    std::vector<unsigned char> generatePNG(const std::string& data, const json& design, int size);
    std::vector<unsigned char> generateJPG(const std::string& data, const json& design, int size);
};
