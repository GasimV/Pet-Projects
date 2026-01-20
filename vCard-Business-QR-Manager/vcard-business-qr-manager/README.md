# vCard-Business-QR-Manager - vCard & Business Page QR Code Generator

A simple MVP web application for creating and managing vCard QR codes.

## Project Structure

```
vcard-business-qr-manager/
├── backend/
│   ├── src/
│   │   ├── main.cpp
│   │   ├── auth.hpp
│   │   ├── auth.cpp
│   │   ├── qr_generator.hpp
│   │   ├── qr_generator.cpp
│   │   ├── storage.hpp
│   │   ├── storage.cpp
│   │   ├── templates.hpp
│   │   ├── templates.cpp
│   │   └── utils.hpp
│   ├── libs/
│   │   ├── cpp-httplib/
│   │   ├── json/
│   │   ├── qrcodegen/
│   │   ├── sqlite3/
│   │   └── stb/
│   ├── build/          (generated)
│   └── CMakeLists.txt
├── frontend/
│   └── index.html      (static single-page app)
├── data/               (runtime data directory)
│   ├── vcard-business-qr-manager.db
│   └── uploads/
├── .gitignore
└── README.md
```

## Backend Setup

### Prerequisites
- C++17 or higher
- CMake 3.15+
- Libraries (included in project):
  - cpp-httplib (HTTP server)
  - nlohmann/json (JSON parsing)
  - QR Code generator (Nayuki)
  - SQLite3
  - stb_image_write (PNG/JPG generation)

### Build Instructions

```bash
cd backend
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

### Running the Backend

```bash
# From backend\build\Release> directory
./vcard-business-qr-manager_qr --port 8080 --data ../../../data

# Or on Windows
.\vcard-business-qr-manager_qr.exe --port 8080 --data ..\..\..\data
```

The backend will:
- Create necessary directories (`./data/uploads/`)
- Initialize SQLite database (`./data/vcard-business-qr-manager.db`)
- Seed admin user: `admin@vcard-business-qr-manager.local` / `Admin123!`
- Start HTTP server on port 8080
- Serve the frontend at `http://localhost:8080`

## Accessing the Application

Once the backend is running, open your web browser and navigate to:

```
http://localhost:8080
```

The backend serves the frontend automatically - no separate frontend build or server is needed.

## Default Credentials

- **Email**: `admin@vcard-business-qr-manager.local`
- **Password**: `Admin123!`

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email/password
- `GET /api/me` - Get current user info

### QR Codes
- `GET /api/qr-codes?search=` - List QR codes with optional search
- `POST /api/qr-codes` - Create new vCard QR code
- `GET /api/qr-codes/{id}` - Get QR code details
- `PUT /api/qr-codes/{id}` - Update QR code
- `DELETE /api/qr-codes/{id}` - Delete QR code
- `PATCH /api/qr-codes/{id}/status` - Toggle active/inactive

### Uploads
- `POST /api/uploads` - Upload profile image or logo (multipart/form-data)

### Rendering
- `GET /api/qr-codes/{id}/render.svg` - Download as SVG
- `GET /api/qr-codes/{id}/render.png?size=512` - Download as PNG
- `GET /api/qr-codes/{id}/render.jpg?size=512` - Download as JPG

### Analytics
- `GET /api/qr-codes/{id}/analytics` - Get scan statistics

### Public
- `GET /q/{shortCode}` - Public landing page (logs scan)
- `GET /q/{shortCode}/vcard.vcf` - Download vCard file

## Features Implemented

### Dashboard
- ✅ Search QR codes by name
- ✅ Table view with preview, name, type, scans, status, date
- ✅ Share (copy public URL)
- ✅ Download (PNG/SVG/JPG)
- ✅ Edit/Delete/Activate/Deactivate actions

### Create QR Code Wizard
- ✅ Step 1: Choose type (vCard only enabled)
- ✅ Step 2: Add vCard content
  - Design and customize (color presets + custom colors)
  - About you (name, profile image)
  - Contact details (phone, email, website)
  - Company details (company, title)
  - Summary text
  - Social networks (icon grid)
  - QR code name
- ✅ Step 3: Customize QR design
  - Primary/secondary colors
  - Logo upload
  - Frame presets (5 options)
  - Pattern presets (square, rounded, dots)
- ✅ Live preview (landing page + QR code)

### Public Landing Page
- ✅ Mobile-optimized vCard page
- ✅ Profile photo
- ✅ Name and "Add contact" button
- ✅ Contact, Company, Summary sections
- ✅ Social media links
- ✅ Scan tracking

### Analytics
- ✅ Total scans counter
- ✅ Last scanned timestamp
- ✅ Device type detection (from User-Agent)
- ✅ Basic analytics display

## Technology Stack

### Backend
- **Language**: C++17
- **HTTP Server**: cpp-httplib
- **Database**: SQLite3
- **QR Generation**: Nayuki QR Code generator
- **Image Export**: stb_image_write
- **JSON**: nlohmann/json
- **Auth**: JWT (simple implementation)

### Frontend
- **Type**: Vanilla JavaScript SPA (Single Page Application)
- **Styling**: Custom CSS with CSS Variables
- **Architecture**: Component-based UI with state management
- **Build**: No build process required - served directly as static HTML

## Data Storage

All data is stored locally:
- **Database**: `./data/vcard-business-qr-manager.db` (SQLite)
- **Uploads**: `./data/uploads/` (images, logos)

The database persists:
- Users (with hashed passwords)
- QR codes (with vCard and design data)
- Scan events (with device/timestamp info)

## Security Notes

This is an MVP for internal use:
- JWT tokens have 7-day expiration
- Passwords are hashed (bcrypt-style)
- File uploads limited to 5MB
- No rate limiting implemented
- No HTTPS (use reverse proxy for production)

## Known Limitations

- Single-user seeded admin account
- No user registration UI
- No email verification
- No forgot password flow
- Country/location detection not implemented (returns "unknown")
- Frame overlays are simple text labels (not complex SVG frames)

## Future Enhancements

- Multi-user support with proper signup
- Email notifications
- Advanced analytics (geolocation, time-based charts)
- More QR code types (URL, PDF, etc.)
- Batch operations
- QR code templates
- Custom domains for short URLs
- API rate limiting

## Quick Start

1. **Build the backend:**
   ```bash
   cd backend
   mkdir build && cd build
   cmake ..
   cmake --build . --config Release
   ```

2. **Run the server:**
   ```bash
   cd Release
   .\vcard-business-qr-manager_qr.exe --port 8080 --data ..\..\..\data
   ```

3. **Open in browser:**
   ```
   http://localhost:8080
   ```

4. **Login with default credentials:**
   - Email: `admin@vcard-business-qr-manager.local`
   - Password: `Admin123!`

## Author

Gasym A. Valiyev
