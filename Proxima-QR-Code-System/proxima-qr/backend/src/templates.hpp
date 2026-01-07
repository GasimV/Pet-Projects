#pragma once
#include <string>
#include "nlohmann/json.hpp"

using json = nlohmann::json;

std::string generateVCardLandingPage(const json& vcard, const json& design, const std::string& shortCode);
std::string generateVCF(const json& vcard);
