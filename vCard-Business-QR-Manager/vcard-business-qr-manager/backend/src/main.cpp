// main.cpp - vcard-business-qr-manager QR Backend Entry Point
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

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <ifaddrs.h>
#include <netdb.h>
#include <arpa/inet.h>
#endif

using json = nlohmann::json;
namespace fs = std::filesystem;

// Global instances
Storage storage;
Auth auth;
QRGenerator qrGen;
std::string baseUrl = "http://localhost:8080";

// Get local IP address (Wi-Fi)
std::string getLocalIP() {
#ifdef _WIN32
    // Windows implementation
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        return "localhost";
    }

    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) == SOCKET_ERROR) {
        WSACleanup();
        return "localhost";
    }

    struct addrinfo hints, *result = nullptr;
    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    if (getaddrinfo(hostname, nullptr, &hints, &result) != 0) {
        WSACleanup();
        return "localhost";
    }

    std::string fallbackIP;
    for (struct addrinfo* ptr = result; ptr != nullptr; ptr = ptr->ai_next) {
        struct sockaddr_in* sockaddr_ipv4 = (struct sockaddr_in*)ptr->ai_addr;
        char ipStr[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &sockaddr_ipv4->sin_addr, ipStr, INET_ADDRSTRLEN);

        std::string ip(ipStr);
        // Skip loopback
        if (ip.find("127.") != 0) {
            // Prioritize 192.168.x.x (home Wi-Fi) over other private networks
            if (ip.find("192.168.") == 0) {
                freeaddrinfo(result);
                WSACleanup();
                return ip;
            }
            // Save as fallback if no 192.168.x.x found
            if (fallbackIP.empty()) {
                fallbackIP = ip;
            }
        }
    }

    freeaddrinfo(result);
    WSACleanup();
    return fallbackIP.empty() ? "localhost" : fallbackIP;
#else
    // Unix/Linux implementation
    struct ifaddrs *ifaddr, *ifa;
    char host[NI_MAXHOST];

    if (getifaddrs(&ifaddr) == -1) {
        return "localhost";
    }

    for (ifa = ifaddr; ifa != nullptr; ifa = ifa->ifa_next) {
        if (ifa->ifa_addr == nullptr) continue;

        int family = ifa->ifa_addr->sa_family;
        if (family == AF_INET) {
            int s = getnameinfo(ifa->ifa_addr, sizeof(struct sockaddr_in),
                               host, NI_MAXHOST, nullptr, 0, NI_NUMERICHOST);
            if (s == 0) {
                std::string ip(host);
                // Skip loopback and look for typical local network IPs
                if (ip.find("127.") != 0 && (ip.find("192.168.") == 0 || ip.find("10.") == 0 || ip.find("172.") == 0)) {
                    freeifaddrs(ifaddr);
                    return ip;
                }
            }
        }
    }

    freeifaddrs(ifaddr);
    return "localhost";
#endif
}

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

    // Get local IP and set base URL
    std::string localIP = getLocalIP();
    baseUrl = "http://" + localIP + ":" + std::to_string(port);

    // Initialize directories
    fs::create_directories(dataPath);
    fs::create_directories(dataPath + "/uploads");
    
    // Initialize storage
    if (!storage.init(dataPath + "/vcard-business-qr-manager.db")) {
        std::cerr << "Failed to initialize storage" << std::endl;
        return 1;
    }
    
    // Initialize auth with storage reference
    auth.init(&storage);
    
    std::cout << "vcard-business-qr-manager QR Backend starting..." << std::endl;
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

            std::string type = body.value("type", "vcard");

            // Type-specific validation
            if (type == "vcard") {
                if (!body.contains("vcard") || !body["vcard"].contains("fullName") ||
                    body["vcard"]["fullName"].get<std::string>().empty()) {
                    res.status = 400;
                    json error = {{"error", "Full name is required for vCard"}};
                    res.set_content(error.dump(), "application/json");
                    return;
                }
            } else if (type == "businesspage") {
                if (!body.contains("businesspage") || !body["businesspage"].contains("companyName") ||
                    body["businesspage"]["companyName"].get<std::string>().empty()) {
                    res.status = 400;
                    json error = {{"error", "Company name is required for Business Page"}};
                    res.set_content(error.dump(), "application/json");
                    return;
                }
            }

            QRCode qr;
            qr.id = generateUUID();
            qr.userId = userId;
            qr.name = body["name"];
            qr.type = type == "businesspage" ? "BUSINESSPAGE" : "VCARD";
            qr.status = "active";
            qr.shortCode = generateShortCode();
            qr.vcardData = body.contains("vcard") ? body["vcard"].dump() : "{}";
            qr.businesspageData = body.contains("businesspage") ? body["businesspage"].dump() : "{}";
            qr.designData = body.contains("design") ? body["design"].dump() : "{}";
            qr.scans = 0;
            qr.createdAt = getCurrentTimestamp();
            qr.updatedAt = qr.createdAt;

            if (storage.createQRCode(qr)) {
                json response = {
                    {"id", qr.id},
                    {"name", qr.name},
                    {"shortCode", qr.shortCode},
                    {"publicUrl", baseUrl + "/q/" + qr.shortCode}
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
            json businesspage = json::parse(qr->businesspageData);
            json design = json::parse(qr->designData);

            json response = {
                {"id", qr->id},
                {"name", qr->name},
                {"type", qr->type == "BUSINESSPAGE" ? "Business Page" : "vCard"},
                {"status", qr->status},
                {"shortCode", qr->shortCode},
                {"scans", qr->scans},
                {"vcard", vcard},
                {"businesspage", businesspage},
                {"design", design},
                {"createdAt", qr->createdAt},
                {"updatedAt", qr->updatedAt},
                {"publicUrl", baseUrl + "/q/" + qr->shortCode}
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
            qr->businesspageData = body.contains("businesspage") ? body["businesspage"].dump() : qr->businesspageData;
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
        std::string publicUrl = baseUrl + "/q/" + qr->shortCode;

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
        std::string publicUrl = baseUrl + "/q/" + qr->shortCode;

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
        std::string publicUrl = baseUrl + "/q/" + qr->shortCode;

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

        // Generate landing page based on type
        json design = json::parse(qr->designData);
        std::string html;

        if (qr->type == "BUSINESSPAGE") {
            json businesspage = json::parse(qr->businesspageData);
            html = generateBusinessPageLandingPage(businesspage, design, shortCode);
        } else {
            json vcard = json::parse(qr->vcardData);
            html = generateVCardLandingPage(vcard, design, shortCode);
        }

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
    std::cout << "Base URL: " << baseUrl << std::endl;
    std::cout << "Admin credentials: admin@vcard-business-qr-manager.local / Admin123!" << std::endl;
    std::cout << "Frontend accessible at: " << baseUrl << std::endl;

    svr.listen("0.0.0.0", port);
    
    return 0;
}