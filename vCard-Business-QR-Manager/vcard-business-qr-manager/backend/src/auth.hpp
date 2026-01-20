// auth.hpp - Authentication module
#ifndef AUTH_HPP
#define AUTH_HPP

#include <string>
#include <map>
#include <chrono>
#include "nlohmann/json.hpp"

class Storage; // Forward declaration

struct LoginResult {
    bool success;
    std::string token;
    std::string userId;
};

class Auth {
private:
    Storage* storage;
    std::map<std::string, std::pair<std::string, std::chrono::system_clock::time_point>> tokens; // token -> (userId, expiry)
    
    std::string generateToken();
    
public:
    void init(Storage* storage);
    LoginResult login(const std::string& email, const std::string& password);
    bool validateToken(const std::string& token, std::string& userId);
};

#endif // AUTH_HPP