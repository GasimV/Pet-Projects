// ============================================
// storage.cpp - Storage implementation
// ============================================

#include "storage.hpp"
#include "utils.hpp"
#include <iostream>
#include <sstream>

Storage::Storage() : db(nullptr) {}

Storage::~Storage() {
    if (db) {
        sqlite3_close(db);
    }
}

bool Storage::execute(const std::string& sql) {
    char* errMsg = nullptr;
    int rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, &errMsg);
    
    if (rc != SQLITE_OK) {
        std::cerr << "SQL error: " << errMsg << std::endl;
        sqlite3_free(errMsg);
        return false;
    }
    
    return true;
}

bool Storage::init(const std::string& dbPath) {
    int rc = sqlite3_open(dbPath.c_str(), &db);
    
    if (rc != SQLITE_OK) {
        std::cerr << "Cannot open database: " << sqlite3_errmsg(db) << std::endl;
        return false;
    }
    
    // Create tables
    execute(R"(
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    )");
    
    execute(R"(
        CREATE TABLE IF NOT EXISTS qr_codes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            short_code TEXT UNIQUE NOT NULL,
            vcard_data TEXT,
            design_data TEXT,
            scans INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    )");
    
    execute(R"(
        CREATE TABLE IF NOT EXISTS scan_events (
            id TEXT PRIMARY KEY,
            qr_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_agent TEXT,
            device_type TEXT,
            FOREIGN KEY (qr_id) REFERENCES qr_codes(id)
        )
    )");
    
    // Seed admin user if not exists
    auto adminUser = getUserByEmail("admin@proxima.local");
    if (!adminUser) {
        User admin;
        admin.id = generateUUID();
        admin.email = "admin@proxima.local";
        admin.passwordHash = hashPassword("Admin123!");
        admin.role = "ADMIN";
        createUser(admin);
        std::cout << "Admin user seeded" << std::endl;
    }
    
    return true;
}

// User operations
std::optional<User> Storage::getUser(const std::string& id) {
    sqlite3_stmt* stmt;
    const char* sql = "SELECT id, email, password_hash, role FROM users WHERE id = ?";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return std::nullopt;
    }
    
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_STATIC);
    
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        User user;
        user.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        user.email = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        user.passwordHash = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        user.role = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        
        sqlite3_finalize(stmt);
        return user;
    }
    
    sqlite3_finalize(stmt);
    return std::nullopt;
}

std::optional<User> Storage::getUserByEmail(const std::string& email) {
    sqlite3_stmt* stmt;
    const char* sql = "SELECT id, email, password_hash, role FROM users WHERE email = ?";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return std::nullopt;
    }
    
    sqlite3_bind_text(stmt, 1, email.c_str(), -1, SQLITE_STATIC);
    
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        User user;
        user.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        user.email = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        user.passwordHash = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        user.role = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        
        sqlite3_finalize(stmt);
        return user;
    }
    
    sqlite3_finalize(stmt);
    return std::nullopt;
}

bool Storage::createUser(const User& user) {
    sqlite3_stmt* stmt;
    const char* sql = "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    sqlite3_bind_text(stmt, 1, user.id.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, user.email.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, user.passwordHash.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, user.role.c_str(), -1, SQLITE_STATIC);
    
    bool success = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return success;
}

// QR Code operations
std::vector<QRCode> Storage::getQRCodes(const std::string& userId, const std::string& search) {
    std::vector<QRCode> qrCodes;
    sqlite3_stmt* stmt;
    
    std::string sql = "SELECT id, user_id, name, type, status, short_code, vcard_data, design_data, scans, created_at, updated_at FROM qr_codes WHERE user_id = ?";
    
    if (!search.empty()) {
        sql += " AND name LIKE ?";
    }
    
    sql += " ORDER BY created_at DESC";
    
    if (sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        return qrCodes;
    }
    
    sqlite3_bind_text(stmt, 1, userId.c_str(), -1, SQLITE_STATIC);
    
    if (!search.empty()) {
        std::string searchPattern = "%" + search + "%";
        sqlite3_bind_text(stmt, 2, searchPattern.c_str(), -1, SQLITE_TRANSIENT);
    }
    
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        QRCode qr;
        qr.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        qr.userId = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        qr.name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        qr.type = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        qr.status = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 4));
        qr.shortCode = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 5));
        qr.vcardData = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 6));
        qr.designData = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 7));
        qr.scans = sqlite3_column_int(stmt, 8);
        qr.createdAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 9));
        qr.updatedAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 10));
        
        qrCodes.push_back(qr);
    }
    
    sqlite3_finalize(stmt);
    return qrCodes;
}

std::optional<QRCode> Storage::getQRCode(const std::string& id) {
    sqlite3_stmt* stmt;
    const char* sql = "SELECT id, user_id, name, type, status, short_code, vcard_data, design_data, scans, created_at, updated_at FROM qr_codes WHERE id = ?";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return std::nullopt;
    }
    
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_STATIC);
    
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        QRCode qr;
        qr.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        qr.userId = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        qr.name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        qr.type = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        qr.status = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 4));
        qr.shortCode = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 5));
        qr.vcardData = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 6));
        qr.designData = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 7));
        qr.scans = sqlite3_column_int(stmt, 8);
        qr.createdAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 9));
        qr.updatedAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 10));
        
        sqlite3_finalize(stmt);
        return qr;
    }
    
    sqlite3_finalize(stmt);
    return std::nullopt;
}

std::optional<QRCode> Storage::getQRCodeByShortCode(const std::string& shortCode) {
    sqlite3_stmt* stmt;
    const char* sql = "SELECT id, user_id, name, type, status, short_code, vcard_data, design_data, scans, created_at, updated_at FROM qr_codes WHERE short_code = ?";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return std::nullopt;
    }
    
    sqlite3_bind_text(stmt, 1, shortCode.c_str(), -1, SQLITE_STATIC);
    
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        QRCode qr;
        qr.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        qr.userId = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        qr.name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        qr.type = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        qr.status = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 4));
        qr.shortCode = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 5));
        qr.vcardData = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 6));
        qr.designData = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 7));
        qr.scans = sqlite3_column_int(stmt, 8);
        qr.createdAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 9));
        qr.updatedAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 10));
        
        // Increment scans count
        execute("UPDATE qr_codes SET scans = scans + 1 WHERE id = '" + qr.id + "'");
        
        sqlite3_finalize(stmt);
        return qr;
    }
    
    sqlite3_finalize(stmt);
    return std::nullopt;
}

bool Storage::createQRCode(const QRCode& qr) {
    sqlite3_stmt* stmt;
    const char* sql = "INSERT INTO qr_codes (id, user_id, name, type, status, short_code, vcard_data, design_data, scans, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    sqlite3_bind_text(stmt, 1, qr.id.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, qr.userId.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, qr.name.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, qr.type.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 5, qr.status.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 6, qr.shortCode.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 7, qr.vcardData.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 8, qr.designData.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int(stmt, 9, qr.scans);
    sqlite3_bind_text(stmt, 10, qr.createdAt.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 11, qr.updatedAt.c_str(), -1, SQLITE_STATIC);
    
    bool success = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return success;
}

bool Storage::updateQRCode(const QRCode& qr) {
    sqlite3_stmt* stmt;
    const char* sql = "UPDATE qr_codes SET name = ?, status = ?, vcard_data = ?, design_data = ?, updated_at = ? WHERE id = ?";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    sqlite3_bind_text(stmt, 1, qr.name.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, qr.status.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, qr.vcardData.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, qr.designData.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 5, qr.updatedAt.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 6, qr.id.c_str(), -1, SQLITE_STATIC);
    
    bool success = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return success;
}

bool Storage::deleteQRCode(const std::string& id) {
    // Delete related scan events first
    execute("DELETE FROM scan_events WHERE qr_id = '" + id + "'");
    
    sqlite3_stmt* stmt;
    const char* sql = "DELETE FROM qr_codes WHERE id = ?";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_STATIC);
    
    bool success = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return success;
}

bool Storage::logScan(const std::string& qrId, const std::string& userAgent, const std::string& deviceType) {
    sqlite3_stmt* stmt;
    const char* sql = "INSERT INTO scan_events (id, qr_id, timestamp, user_agent, device_type) VALUES (?, ?, ?, ?, ?)";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    std::string id = generateUUID();
    std::string timestamp = getCurrentTimestamp();
    
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, qrId.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, timestamp.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, userAgent.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 5, deviceType.c_str(), -1, SQLITE_STATIC);
    
    bool success = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return success;
}

json Storage::getAnalytics(const std::string& qrId) {
    json analytics;
    
    // Get QR code
    auto qr = getQRCode(qrId);
    if (!qr) {
        return analytics;
    }
    
    analytics["totalScans"] = qr->scans;
    
    // Get last scanned
    sqlite3_stmt* stmt;
    const char* sql = "SELECT timestamp FROM scan_events WHERE qr_id = ? ORDER BY timestamp DESC LIMIT 1";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, qrId.c_str(), -1, SQLITE_STATIC);
        
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            analytics["lastScanned"] = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        } else {
            analytics["lastScanned"] = nullptr;
        }
        
        sqlite3_finalize(stmt);
    }
    
    // Get by device
    json byDevice = json::object();
    sql = "SELECT device_type, COUNT(*) as count FROM scan_events WHERE qr_id = ? GROUP BY device_type";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, qrId.c_str(), -1, SQLITE_STATIC);
        
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            std::string deviceType = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
            int count = sqlite3_column_int(stmt, 1);
            byDevice[deviceType] = count;
        }
        
        sqlite3_finalize(stmt);
    }
    
    analytics["byDevice"] = byDevice;
    analytics["byCountry"] = json::object({{"unknown", qr->scans}});
    
    return analytics;
}