// ============================================
// auth.cpp - Authentication implementation
// ============================================

#include "auth.hpp"
#include "storage.hpp"
#include "utils.hpp"
#include <algorithm>

void Auth::init(Storage* storagePtr) {
    this->storage = storagePtr;
}

std::string Auth::generateToken() {
    return generateUUID() + generateUUID(); // Simple token for MVP
}

LoginResult Auth::login(const std::string& email, const std::string& password) {
    LoginResult result = {false, "", ""};
    
    auto user = storage->getUserByEmail(email);
    if (!user) {
        return result;
    }
    
    // Verify password
    std::string hashedInput = hashPassword(password);
    if (hashedInput != user->passwordHash) {
        return result;
    }
    
    // Generate token with 7-day expiry
    std::string token = generateToken();
    auto expiry = std::chrono::system_clock::now() + std::chrono::hours(24 * 7);
    
    tokens[token] = {user->id, expiry};
    
    result.success = true;
    result.token = token;
    result.userId = user->id;
    
    return result;
}

bool Auth::validateToken(const std::string& token, std::string& userId) {
    auto it = tokens.find(token);
    if (it == tokens.end()) {
        return false;
    }
    
    // Check expiry
    if (std::chrono::system_clock::now() > it->second.second) {
        tokens.erase(it);
        return false;
    }
    
    userId = it->second.first;
    return true;
}