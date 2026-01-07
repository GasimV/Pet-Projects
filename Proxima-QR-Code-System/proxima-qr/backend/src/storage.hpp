// storage.hpp - Data storage with SQLite
#ifndef STORAGE_HPP
#define STORAGE_HPP

#include <string>
#include <vector>
#include <optional>
#include "sqlite3.h"
#include "nlohmann/json.hpp"

using json = nlohmann::json;

struct User {
    std::string id;
    std::string email;
    std::string passwordHash;
    std::string role;
};

struct QRCode {
    std::string id;
    std::string userId;
    std::string name;
    std::string type;
    std::string status;
    std::string shortCode;
    std::string vcardData;
    std::string designData;
    int scans;
    std::string createdAt;
    std::string updatedAt;
};

struct ScanEvent {
    std::string id;
    std::string qrId;
    std::string timestamp;
    std::string userAgent;
    std::string deviceType;
};

class Storage {
private:
    sqlite3* db;
    
    bool execute(const std::string& sql);
    
public:
    Storage();
    ~Storage();
    
    bool init(const std::string& dbPath);
    
    // User operations
    std::optional<User> getUser(const std::string& id);
    std::optional<User> getUserByEmail(const std::string& email);
    bool createUser(const User& user);
    
    // QR Code operations
    std::vector<QRCode> getQRCodes(const std::string& userId, const std::string& search = "");
    std::optional<QRCode> getQRCode(const std::string& id);
    std::optional<QRCode> getQRCodeByShortCode(const std::string& shortCode);
    bool createQRCode(const QRCode& qr);
    bool updateQRCode(const QRCode& qr);
    bool deleteQRCode(const std::string& id);
    
    // Scan operations
    bool logScan(const std::string& qrId, const std::string& userAgent, const std::string& deviceType);
    json getAnalytics(const std::string& qrId);
};

#endif // STORAGE_HPP