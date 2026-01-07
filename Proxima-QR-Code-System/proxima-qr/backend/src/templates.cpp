#include "templates.hpp"
#include <sstream>

std::string generateVCardLandingPage(const json& vcard, const json& design, const std::string& shortCode) {
    std::string name = vcard.value("name", "");
    std::string email = vcard.value("email", "");
    std::string phone = vcard.value("phone", "");
    std::string website = vcard.value("website", "");
    std::string company = vcard.value("company", "");
    std::string title = vcard.value("title", "");
    std::string summary = vcard.value("summary", "");
    std::string profileImage = vcard.value("profileImage", "");

    std::string primaryColor = design.value("primaryColor", "#3b82f6");
    std::string secondaryColor = design.value("secondaryColor", "#1e40af");

    std::ostringstream html;
    html << R"(<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>)" << name << R"( - Contact</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; min-height: 100vh; }
        .header { background: linear-gradient(135deg, )" << primaryColor << R"(, )" << secondaryColor << R"();
                  padding: 60px 20px; text-align: center; color: white; }
        .avatar { width: 120px; height: 120px; border-radius: 50%; border: 4px solid white; margin: 0 auto 20px;
                  background: white; overflow: hidden; }
        .avatar img { width: 100%; height: 100%; object-fit: cover; }
        .name { font-size: 28px; font-weight: bold; margin-bottom: 10px; }
        .btn { display: inline-block; background: white; color: )" << primaryColor << R"(;
               padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600; margin-top: 20px; }
        .section { padding: 30px 20px; border-bottom: 1px solid #e5e5e5; }
        .section-title { font-size: 12px; text-transform: uppercase; color: #999; margin-bottom: 15px; letter-spacing: 1px; }
        .contact-item { margin-bottom: 15px; }
        .contact-label { font-size: 14px; color: #666; margin-bottom: 5px; }
        .contact-value { font-size: 16px; color: #333; word-break: break-all; }
        .social-links { display: flex; flex-wrap: wrap; gap: 10px; }
        .social-link { display: inline-flex; align-items: center; gap: 8px; background: #f5f5f5;
                       padding: 10px 15px; border-radius: 8px; text-decoration: none; color: #333; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">)";

    if (!profileImage.empty()) {
        html << R"(
            <div class="avatar">
                <img src=")" << profileImage << R"(" alt=")" << name << R"(">
            </div>)";
    }

    html << R"(
            <div class="name">)" << name << R"(</div>
            <a href="/q/)" << shortCode << R"(/vcard.vcf" class="btn">Add Contact</a>
        </div>)";

    // Contact Section
    if (!email.empty() || !phone.empty() || !website.empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">Contact</div>)";

        if (!email.empty()) {
            html << R"(
            <div class="contact-item">
                <div class="contact-label">Email</div>
                <div class="contact-value">)" << email << R"(</div>
            </div>)";
        }

        if (!phone.empty()) {
            html << R"(
            <div class="contact-item">
                <div class="contact-label">Phone</div>
                <div class="contact-value">)" << phone << R"(</div>
            </div>)";
        }

        if (!website.empty()) {
            html << R"(
            <div class="contact-item">
                <div class="contact-label">Website</div>
                <div class="contact-value">)" << website << R"(</div>
            </div>)";
        }

        html << R"(
        </div>)";
    }

    // Company Section
    if (!company.empty() || !title.empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">Company</div>)";

        if (!company.empty()) {
            html << R"(
            <div class="contact-item">
                <div class="contact-label">Company</div>
                <div class="contact-value">)" << company << R"(</div>
            </div>)";
        }

        if (!title.empty()) {
            html << R"(
            <div class="contact-item">
                <div class="contact-label">Title</div>
                <div class="contact-value">)" << title << R"(</div>
            </div>)";
        }

        html << R"(
        </div>)";
    }

    // Summary Section
    if (!summary.empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">About</div>
            <p style="color: #333; line-height: 1.6;">)" << summary << R"(</p>
        </div>)";
    }

    // Social Links Section
    if (vcard.contains("socialLinks") && vcard["socialLinks"].is_object()) {
        auto& social = vcard["socialLinks"];
        bool hasSocial = false;

        for (auto& [key, value] : social.items()) {
            if (!value.get<std::string>().empty()) {
                hasSocial = true;
                break;
            }
        }

        if (hasSocial) {
            html << R"(
        <div class="section">
            <div class="section-title">Social Media</div>
            <div class="social-links">)";

            for (auto& [key, value] : social.items()) {
                std::string url = value.get<std::string>();
                if (!url.empty()) {
                    html << R"(
                <a href=")" << url << R"(" class="social-link" target="_blank">)" << key << R"(</a>)";
                }
            }

            html << R"(
            </div>
        </div>)";
        }
    }

    html << R"(
    </div>
</body>
</html>)";

    return html.str();
}

std::string generateVCF(const json& vcard) {
    std::ostringstream vcf;

    vcf << "BEGIN:VCARD\r\n";
    vcf << "VERSION:3.0\r\n";

    if (vcard.contains("name")) {
        std::string name = vcard["name"].get<std::string>();
        vcf << "FN:" << name << "\r\n";
        vcf << "N:" << name << ";;;;\r\n";
    }

    if (vcard.contains("email")) {
        vcf << "EMAIL;TYPE=INTERNET:" << vcard["email"].get<std::string>() << "\r\n";
    }

    if (vcard.contains("phone")) {
        vcf << "TEL;TYPE=CELL:" << vcard["phone"].get<std::string>() << "\r\n";
    }

    if (vcard.contains("website")) {
        vcf << "URL:" << vcard["website"].get<std::string>() << "\r\n";
    }

    if (vcard.contains("company")) {
        vcf << "ORG:" << vcard["company"].get<std::string>() << "\r\n";
    }

    if (vcard.contains("title")) {
        vcf << "TITLE:" << vcard["title"].get<std::string>() << "\r\n";
    }

    if (vcard.contains("summary")) {
        vcf << "NOTE:" << vcard["summary"].get<std::string>() << "\r\n";
    }

    vcf << "END:VCARD\r\n";

    return vcf.str();
}
