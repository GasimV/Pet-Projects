// main.cpp - Proxima QR Backend Entry Point
#include "httplib.h"
#include "nlohmann/json.hpp"
#include "auth.hpp"
#include "storage.hpp"
#include "qr_generator.hpp"
#include "templates.hpp"
#include "utils.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <cstring>

using json = nlohmann::json;
namespace fs = std::filesystem;

// Global instances
Storage storage;
Auth auth;
QRGenerator qrGen;

// CORS middleware
void addCorsHeaders(httplib::Response& res) {
    res.set_header("Access-Control-Allow-Origin", "*");
    res.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
    res.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization");
}

// JWT validation middleware
bool validateToken(const httplib::Request& req, std::string& userId) {
    auto authHeader = req.get_header_value("Authorization");
    if (authHeader.empty() || authHeader.find("Bearer ") != 0) {
        return false;
    }
    
    std::string token = authHeader.substr(7);
    return auth.validateToken(token, userId);
}

int main(int argc, char* argv[]) {
    // Parse command line arguments
    int port = 8080;
    std::string dataPath = "./data";
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
            port = std::stoi(argv[++i]);
        } else if (strcmp(argv[i], "--data") == 0 && i + 1 < argc) {
            dataPath = argv[++i];
        }
    }
    
    // Initialize directories
    fs::create_directories(dataPath);
    fs::create_directories(dataPath + "/uploads");
    
    // Initialize storage
    if (!storage.init(dataPath + "/proxima.db")) {
        std::cerr << "Failed to initialize storage" << std::endl;
        return 1;
    }
    
    // Initialize auth with storage reference
    auth.init(&storage);
    
    std::cout << "Proxima QR Backend starting..." << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Data path: " << dataPath << std::endl;
    
    httplib::Server svr;

    // Set static file serving for uploads
    svr.set_mount_point("/uploads", (dataPath + "/uploads").c_str());

    // Serve frontend (index.html)
    svr.Get("/", [](const httplib::Request&, httplib::Response& res) {
        std::ifstream file("../../../frontend/index.html");
        if (file) {
            std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
            res.set_content(content, "text/html");
        } else {
            res.status = 404;
            res.set_content("Frontend not found. Please check the path.", "text/plain");
        }
    });

    // OPTIONS handler for CORS preflight
    svr.Options(".*", [](const httplib::Request&, httplib::Response& res) {
        addCorsHeaders(res);
        res.status = 204;
    });
    
    // ============ AUTH ENDPOINTS ============
    
    // POST /api/auth/login
    svr.Post("/api/auth/login", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        try {
            json body = json::parse(req.body);
            std::string email = body["email"];
            std::string password = body["password"];
            
            auto result = auth.login(email, password);
            
            if (result.success) {
                json response = {
                    {"success", true},
                    {"token", result.token},
                    {"user", {
                        {"id", result.userId},
                        {"email", email},
                        {"role", "ADMIN"}
                    }}
                };
                res.set_content(response.dump(), "application/json");
            } else {
                res.status = 401;
                json error = {{"error", "Invalid credentials"}};
                res.set_content(error.dump(), "application/json");
            }
        } catch (const std::exception& e) {
            res.status = 400;
            json error = {{"error", e.what()}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    // GET /api/me
    svr.Get("/api/me", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            json error = {{"error", "Unauthorized"}};
            res.set_content(error.dump(), "application/json");
            return;
        }
        
        auto user = storage.getUser(userId);
        if (user) {
            json response = {
                {"id", user->id},
                {"email", user->email},
                {"role", user->role}
            };
            res.set_content(response.dump(), "application/json");
        } else {
            res.status = 404;
            json error = {{"error", "User not found"}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    // ============ QR CODE ENDPOINTS ============
    
    // GET /api/qr-codes
    svr.Get("/api/qr-codes", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        std::string search = req.has_param("search") ? req.get_param_value("search") : "";
        auto qrCodes = storage.getQRCodes(userId, search);
        
        json response = json::array();
        for (const auto& qr : qrCodes) {
            response.push_back({
                {"id", qr.id},
                {"name", qr.name},
                {"type", "vCard"},
                {"status", qr.status},
                {"shortCode", qr.shortCode},
                {"scans", qr.scans},
                {"createdAt", qr.createdAt},
                {"updatedAt", qr.updatedAt}
            });
        }
        
        res.set_content(response.dump(), "application/json");
    });
    
    // POST /api/qr-codes
    svr.Post("/api/qr-codes", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        try {
            json body = json::parse(req.body);
            
            // Validate required fields
            if (!body.contains("name") || body["name"].get<std::string>().empty()) {
                res.status = 400;
                json error = {{"error", "QR code name is required"}};
                res.set_content(error.dump(), "application/json");
                return;
            }
            
            if (!body.contains("vcard") || !body["vcard"].contains("fullName") || 
                body["vcard"]["fullName"].get<std::string>().empty()) {
                res.status = 400;
                json error = {{"error", "Full name is required"}};
                res.set_content(error.dump(), "application/json");
                return;
            }
            
            QRCode qr;
            qr.id = generateUUID();
            qr.userId = userId;
            qr.name = body["name"];
            qr.type = "VCARD";
            qr.status = "active";
            qr.shortCode = generateShortCode();
            qr.vcardData = body["vcard"].dump();
            qr.designData = body.contains("design") ? body["design"].dump() : "{}";
            qr.scans = 0;
            qr.createdAt = getCurrentTimestamp();
            qr.updatedAt = qr.createdAt;
            
            if (storage.createQRCode(qr)) {
                json response = {
                    {"id", qr.id},
                    {"name", qr.name},
                    {"shortCode", qr.shortCode},
                    {"publicUrl", "http://localhost:8080/q/" + qr.shortCode}
                };
                res.status = 201;
                res.set_content(response.dump(), "application/json");
            } else {
                res.status = 500;
                json error = {{"error", "Failed to create QR code"}};
                res.set_content(error.dump(), "application/json");
            }
        } catch (const std::exception& e) {
            res.status = 400;
            json error = {{"error", e.what()}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    // GET /api/qr-codes/:id
    svr.Get(R"(/api/qr-codes/([^/]+))", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (qr && qr->userId == userId) {
            json vcard = json::parse(qr->vcardData);
            json design = json::parse(qr->designData);
            
            json response = {
                {"id", qr->id},
                {"name", qr->name},
                {"type", "vCard"},
                {"status", qr->status},
                {"shortCode", qr->shortCode},
                {"scans", qr->scans},
                {"vcard", vcard},
                {"design", design},
                {"createdAt", qr->createdAt},
                {"updatedAt", qr->updatedAt},
                {"publicUrl", "http://localhost:8080/q/" + qr->shortCode}
            };
            res.set_content(response.dump(), "application/json");
        } else {
            res.status = 404;
            json error = {{"error", "QR code not found"}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    // PUT /api/qr-codes/:id
    svr.Put(R"(/api/qr-codes/([^/]+))", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr || qr->userId != userId) {
            res.status = 404;
            return;
        }
        
        try {
            json body = json::parse(req.body);
            
            qr->name = body.value("name", qr->name);
            qr->vcardData = body.contains("vcard") ? body["vcard"].dump() : qr->vcardData;
            qr->designData = body.contains("design") ? body["design"].dump() : qr->designData;
            qr->updatedAt = getCurrentTimestamp();
            
            if (storage.updateQRCode(*qr)) {
                json response = {{"success", true}};
                res.set_content(response.dump(), "application/json");
            } else {
                res.status = 500;
            }
        } catch (const std::exception& e) {
            res.status = 400;
            json error = {{"error", e.what()}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    // DELETE /api/qr-codes/:id
    svr.Delete(R"(/api/qr-codes/([^/]+))", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr || qr->userId != userId) {
            res.status = 404;
            return;
        }
        
        if (storage.deleteQRCode(id)) {
            json response = {{"success", true}};
            res.set_content(response.dump(), "application/json");
        } else {
            res.status = 500;
        }
    });
    
    // PATCH /api/qr-codes/:id/status
    svr.Patch(R"(/api/qr-codes/([^/]+)/status)", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr || qr->userId != userId) {
            res.status = 404;
            return;
        }
        
        try {
            json body = json::parse(req.body);
            std::string newStatus = body["status"];
            
            if (newStatus != "active" && newStatus != "inactive") {
                res.status = 400;
                json error = {{"error", "Invalid status"}};
                res.set_content(error.dump(), "application/json");
                return;
            }
            
            qr->status = newStatus;
            qr->updatedAt = getCurrentTimestamp();
            
            if (storage.updateQRCode(*qr)) {
                json response = {{"success", true}, {"status", newStatus}};
                res.set_content(response.dump(), "application/json");
            } else {
                res.status = 500;
            }
        } catch (const std::exception& e) {
            res.status = 400;
            json error = {{"error", e.what()}};
            res.set_content(error.dump(), "application/json");
        }
    });
    
    // ============ UPLOAD ENDPOINT ============
    
    // POST /api/uploads
    svr.Post("/api/uploads", [&dataPath](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        if (!req.form.has_file("file")) {
            res.status = 400;
            json error = {{"error", "No file provided"}};
            res.set_content(error.dump(), "application/json");
            return;
        }

        auto file = req.form.get_file("file");
        if (file.content.empty()) {
            res.status = 400;
            json error = {{"error", "No file provided"}};
            res.set_content(error.dump(), "application/json");
            return;
        }
        
        // Validate file size (5MB limit)
        if (file.content.size() > 5 * 1024 * 1024) {
            res.status = 400;
            json error = {{"error", "File size exceeds 5MB limit"}};
            res.set_content(error.dump(), "application/json");
            return;
        }
        
        // Validate file type
        std::string contentType = file.content_type;
        std::string extension;
        if (contentType.find("image/jpeg") != std::string::npos || contentType.find("image/jpg") != std::string::npos) {
            extension = ".jpg";
        } else if (contentType.find("image/png") != std::string::npos) {
            extension = ".png";
        } else if (contentType.find("image/svg") != std::string::npos) {
            extension = ".svg";
        } else {
            res.status = 400;
            json error = {{"error", "Invalid file type. Only JPG, PNG, SVG allowed"}};
            res.set_content(error.dump(), "application/json");
            return;
        }
        
        // Generate unique filename
        std::string fileId = generateUUID();
        std::string filename = fileId + extension;
        std::string filepath = dataPath + "/uploads/" + filename;
        
        // Save file
        std::ofstream ofs(filepath, std::ios::binary);
        ofs.write(reinterpret_cast<const char*>(file.content.data()), file.content.size());
        ofs.close();
        
        json response = {
            {"fileId", fileId},
            {"filename", filename},
            {"url", "/uploads/" + filename}
        };
        res.set_content(response.dump(), "application/json");
    });
    
    // ============ RENDER ENDPOINTS ============
    
    // GET /api/qr-codes/:id/render.svg
    svr.Get(R"(/api/qr-codes/([^/]+)/render\.svg)", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr) {
            res.status = 404;
            return;
        }
        
        json design = json::parse(qr->designData);
        std::string publicUrl = "http://localhost:8080/q/" + qr->shortCode;
        
        std::string svg = qrGen.generateSVG(publicUrl, design);
        res.set_content(svg, "image/svg+xml");
        res.set_header("Content-Disposition", "attachment; filename=\"" + qr->name + ".svg\"");
    });
    
    // GET /api/qr-codes/:id/render.png
    svr.Get(R"(/api/qr-codes/([^/]+)/render\.png)", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr) {
            res.status = 404;
            return;
        }
        
        int size = req.has_param("size") ? std::stoi(req.get_param_value("size")) : 512;
        json design = json::parse(qr->designData);
        std::string publicUrl = "http://localhost:8080/q/" + qr->shortCode;
        
        std::vector<unsigned char> png = qrGen.generatePNG(publicUrl, design, size);
        res.set_content(std::string(png.begin(), png.end()), "image/png");
        res.set_header("Content-Disposition", "attachment; filename=\"" + qr->name + ".png\"");
    });
    
    // GET /api/qr-codes/:id/render.jpg
    svr.Get(R"(/api/qr-codes/([^/]+)/render\.jpg)", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr) {
            res.status = 404;
            return;
        }
        
        int size = req.has_param("size") ? std::stoi(req.get_param_value("size")) : 512;
        json design = json::parse(qr->designData);
        std::string publicUrl = "http://localhost:8080/q/" + qr->shortCode;
        
        std::vector<unsigned char> jpg = qrGen.generateJPG(publicUrl, design, size);
        res.set_content(std::string(jpg.begin(), jpg.end()), "image/jpeg");
        res.set_header("Content-Disposition", "attachment; filename=\"" + qr->name + ".jpg\"");
    });
    
    // ============ ANALYTICS ENDPOINT ============
    
    // GET /api/qr-codes/:id/analytics
    svr.Get(R"(/api/qr-codes/([^/]+)/analytics)", [](const httplib::Request& req, httplib::Response& res) {
        addCorsHeaders(res);
        
        std::string userId;
        if (!validateToken(req, userId)) {
            res.status = 401;
            return;
        }
        
        std::string id = req.matches[1];
        auto qr = storage.getQRCode(id);
        
        if (!qr || qr->userId != userId) {
            res.status = 404;
            return;
        }
        
        auto analytics = storage.getAnalytics(id);
        res.set_content(analytics.dump(), "application/json");
    });
    
    // ============ PUBLIC ENDPOINTS ============
    
    // GET /q/:shortCode
    svr.Get(R"(/q/([^/]+))", [](const httplib::Request& req, httplib::Response& res) {
        std::string shortCode = req.matches[1];
        auto qr = storage.getQRCodeByShortCode(shortCode);
        
        if (!qr || qr->status != "active") {
            res.status = 404;
            res.set_content("<h1>QR Code not found</h1>", "text/html");
            return;
        }
        
        // Log scan
        std::string userAgent = req.get_header_value("User-Agent");
        std::string deviceType = detectDeviceType(userAgent);
        storage.logScan(qr->id, userAgent, deviceType);
        
        // Generate landing page
        json vcard = json::parse(qr->vcardData);
        json design = json::parse(qr->designData);
        std::string html = generateVCardLandingPage(vcard, design, shortCode);
        
        res.set_content(html, "text/html");
    });
    
    // GET /q/:shortCode/vcard.vcf
    svr.Get(R"(/q/([^/]+)/vcard\.vcf)", [](const httplib::Request& req, httplib::Response& res) {
        std::string shortCode = req.matches[1];
        auto qr = storage.getQRCodeByShortCode(shortCode);
        
        if (!qr) {
            res.status = 404;
            return;
        }
        
        json vcard = json::parse(qr->vcardData);
        std::string vcf = generateVCF(vcard);
        
        res.set_content(vcf, "text/vcard");
        res.set_header("Content-Disposition", "attachment; filename=\"contact.vcf\"");
    });
    
    std::cout << "Server started on port " << port << std::endl;
    std::cout << "Admin credentials: admin@proxima.local / Admin123!" << std::endl;
    
    svr.listen("0.0.0.0", port);
    
    return 0;
}