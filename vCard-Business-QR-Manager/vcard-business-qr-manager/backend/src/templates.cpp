#include "templates.hpp"
#include <sstream>

std::string generateBusinessPageLandingPage(const json& businesspage, const json& design, const std::string& shortCode) {
    std::string companyName = businesspage.value("companyName", "");
    std::string title = businesspage.value("title", "");
    std::string subtitle = businesspage.value("subtitle", "");
    std::string businessImage = businesspage.value("businessImage", "");
    std::string fullName = businesspage.value("fullName", "");
    std::string phone = businesspage.value("phone", "");
    std::string altPhone = businesspage.value("altPhone", "");
    std::string website = businesspage.value("website", "");
    std::string email = businesspage.value("email", "");
    std::string street = businesspage.value("street", "");
    std::string postalCode = businesspage.value("postalCode", "");
    std::string city = businesspage.value("city", "");
    std::string state = businesspage.value("state", "");
    std::string country = businesspage.value("country", "");
    std::string summary = businesspage.value("summary", "");

    std::string primaryColor = design.value("primaryColor", "#3b82f6");
    std::string secondaryColor = design.value("secondaryColor", "#1e40af");

    std::ostringstream html;
    html << R"(<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>)" << companyName << R"(</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; min-height: 100vh; }
        .header { background: linear-gradient(135deg, )" << primaryColor << R"(, )" << secondaryColor << R"();
                  padding: 40px 20px; text-align: center; color: white; }
        .logo { width: 160px; height: 160px; border-radius: 16px; margin: 0 auto 20px;
                  background: white; overflow: hidden; }
        .logo img { width: 100%; height: 100%; object-fit: cover; }
        .company-name { font-size: 28px; font-weight: bold; margin-bottom: 8px; }
        .company-subtitle { font-size: 16px; opacity: 0.95; margin-bottom: 4px; }
        .company-title { font-size: 14px; opacity: 0.85; }
        .btn { display: inline-block; background: white; color: )" << primaryColor << R"(;
               padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600; margin-top: 20px; }
        .section { padding: 24px 20px; border-bottom: 1px solid #e5e5e5; }
        .section-title { font-size: 12px; text-transform: uppercase; color: #999; margin-bottom: 15px; letter-spacing: 1px; }
        .info-item { margin-bottom: 12px; display: flex; align-items: flex-start; gap: 10px; }
        .info-label { font-size: 14px; color: #666; min-width: 90px; }
        .info-value { font-size: 15px; color: #333; word-break: break-word; flex: 1; }
        .facilities { display: flex; flex-wrap: wrap; gap: 8px; }
        .facility-chip { background: #f0f0f0; padding: 8px 12px; border-radius: 8px; font-size: 13px; }
        .hours-row { margin-bottom: 10px; display: flex; justify-content: space-between; }
        .day { font-weight: 600; color: #333; }
        .time { color: #666; }
        .social-links { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
        .social-link { display: inline-flex; align-items: center; gap: 8px; background: #f5f5f5;
                       padding: 10px 15px; border-radius: 8px; text-decoration: none; color: #333; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">)";

    if (!businessImage.empty()) {
        html << R"(
            <div class="logo">
                <img src=")" << businessImage << R"(" alt=")" << companyName << R"(">
            </div>)";
    }

    html << R"(
            <div class="company-name">)" << companyName << R"(</div>)";

    if (!subtitle.empty()) {
        html << R"(
            <div class="company-subtitle">)" << subtitle << R"(</div>)";
    }

    if (!title.empty()) {
        html << R"(
            <div class="company-title">)" << title << R"(</div>)";
    }

    if (!website.empty()) {
        html << R"(
            <a href=")" << website << R"(" class="btn">Learn more</a>)";
    }

    html << R"(
        </div>)";

    // Contact Section
    if (!fullName.empty() || !phone.empty() || !altPhone.empty() || !email.empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">Contact Information</div>)";

        if (!fullName.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Full name</div>
                <div class="info-value">)" << fullName << R"(</div>
            </div>)";
        }

        if (!phone.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Phone</div>
                <div class="info-value">)" << phone << R"(</div>
            </div>)";
        }

        if (!altPhone.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Alt. Phone</div>
                <div class="info-value">)" << altPhone << R"(</div>
            </div>)";
        }

        if (!email.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Email</div>
                <div class="info-value">)" << email << R"(</div>
            </div>)";
        }

        if (!website.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Website</div>
                <div class="info-value">)" << website << R"(</div>
            </div>)";
        }

        html << R"(
        </div>)";
    }

    // Location Section
    if (!street.empty() || !city.empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">Location</div>)";

        if (!street.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Street</div>
                <div class="info-value">)" << street << R"(</div>
            </div>)";
        }

        std::string cityState = city;
        if (!state.empty()) {
            if (!cityState.empty()) cityState += ", ";
            cityState += state;
        }
        if (!postalCode.empty()) {
            if (!cityState.empty()) cityState += " ";
            cityState += postalCode;
        }

        if (!cityState.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">City</div>
                <div class="info-value">)" << cityState << R"(</div>
            </div>)";
        }

        if (!country.empty()) {
            html << R"(
            <div class="info-item">
                <div class="info-label">Country</div>
                <div class="info-value">)" << country << R"(</div>
            </div>)";
        }

        html << R"(
        </div>)";
    }

    // Opening Hours Section
    if (businesspage.contains("openingHours")) {
        auto& hours = businesspage["openingHours"];
        bool hasHours = false;

        // Check if any hours are enabled
        if (hours.contains("monFri") && hours["monFri"].value("enabled", false)) hasHours = true;

        if (hasHours) {
            html << R"(
        <div class="section">
            <div class="section-title">Open hours</div>)";

            if (hours.contains("monFri") && hours["monFri"].value("enabled", false)) {
                std::string start = hours["monFri"].value("start", "");
                std::string end = hours["monFri"].value("end", "");
                if (!start.empty() && !end.empty()) {
                    html << R"(
            <div class="hours-row">
                <div class="day">Monday - Friday</div>
                <div class="time">)" << start << " - " << end << R"(</div>
            </div>)";
                }
            }

            html << R"(
        </div>)";
        }
    }

    // Facilities Section
    if (businesspage.contains("facilities") && businesspage["facilities"].is_array() && !businesspage["facilities"].empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">Facilities</div>
            <div class="facilities">)";

        for (const auto& facility : businesspage["facilities"]) {
            std::string fac = facility.get<std::string>();
            html << R"(
                <div class="facility-chip">)" << fac << R"(</div>)";
        }

        html << R"(
            </div>
        </div>)";
    }

    // About Section
    if (!summary.empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">About the company</div>
            <p style="color: #333; line-height: 1.6;">)" << summary << R"(</p>
        </div>)";
    }

    // Social Links Section
    if (businesspage.contains("socialLinks") && businesspage["socialLinks"].is_array() && !businesspage["socialLinks"].empty()) {
        html << R"(
        <div class="section">
            <div class="section-title">Social networks</div>
            <div class="social-links">)";

        for (const auto& social : businesspage["socialLinks"]) {
            std::string platform = social.value("platform", "");
            std::string url = social.value("url", "");
            if (!url.empty()) {
                html << R"(
                <a href=")" << url << R"(" class="social-link" target="_blank">)" << platform << R"(</a>)";
            }
        }

        html << R"(
            </div>
        </div>)";
    }

    html << R"(
    </div>
</body>
</html>)";

    return html.str();
}

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
