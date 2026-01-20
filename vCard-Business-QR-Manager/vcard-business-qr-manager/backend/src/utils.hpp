// utils.hpp - Utility functions
#ifndef UTILS_HPP
#define UTILS_HPP

#include <string>
#include <random>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <algorithm>

// Generate UUID v4
inline std::string generateUUID() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    static std::uniform_int_distribution<> dis2(8, 11);
    
    std::stringstream ss;
    ss << std::hex;
    for (int i = 0; i < 8; i++) ss << dis(gen);
    ss << "-";
    for (int i = 0; i < 4; i++) ss << dis(gen);
    ss << "-4";
    for (int i = 0; i < 3; i++) ss << dis(gen);
    ss << "-";
    ss << dis2(gen);
    for (int i = 0; i < 3; i++) ss << dis(gen);
    ss << "-";
    for (int i = 0; i < 12; i++) ss << dis(gen);
    
    return ss.str();
}

// Generate short code for URLs
inline std::string generateShortCode() {
    static const char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, sizeof(charset) - 2);
    
    std::string code;
    for (int i = 0; i < 8; i++) {
        code += charset[dis(gen)];
    }
    return code;
}

// Get current timestamp in ISO 8601 format
inline std::string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
    return ss.str();
}

// Simple password hashing (using basic hash for MVP - use bcrypt in production)
inline std::string hashPassword(const std::string& password) {
    std::hash<std::string> hasher;
    size_t hash = hasher(password + "proxima_salt_2025");
    std::stringstream ss;
    ss << std::hex << hash;
    return ss.str();
}

// Detect device type from User-Agent
inline std::string detectDeviceType(const std::string& userAgent) {
    std::string ua = userAgent;
    std::transform(ua.begin(), ua.end(), ua.begin(), ::tolower);
    
    if (ua.find("mobile") != std::string::npos || 
        ua.find("android") != std::string::npos || 
        ua.find("iphone") != std::string::npos) {
        return "mobile";
    } else if (ua.find("tablet") != std::string::npos || 
               ua.find("ipad") != std::string::npos) {
        return "tablet";
    } else {
        return "desktop";
    }
}

// URL encode
inline std::string urlEncode(const std::string& value) {
    std::ostringstream escaped;
    escaped.fill('0');
    escaped << std::hex;

    for (char c : value) {
        if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
            escaped << c;
        } else {
            escaped << std::uppercase;
            escaped << '%' << std::setw(2) << int((unsigned char)c);
            escaped << std::nouppercase;
        }
    }

    return escaped.str();
}

#endif // UTILS_HPP