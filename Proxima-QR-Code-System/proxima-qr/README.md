# Proxima QR - vCard QR Code Generator

A simple MVP web application for creating and managing vCard QR codes.

## Project Structure

```
proxima-qr/
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
│   └── CMakeLists.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── types/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
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
# From backend/build directory
./proxima_qr --port 8080 --data ../data

# Or on Windows
.\proxima_qr.exe --port 8080 --data ..\data
```

The backend will:
- Create necessary directories (`./data/uploads/`)
- Initialize SQLite database (`./data/proxima.db`)
- Seed admin user: `admin@proxima.local` / `Admin123!`
- Start HTTP server on port 8080

## Frontend Setup

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Running the Frontend

```bash
npm run dev
```

The frontend will start on `http://localhost:5173` and connect to backend at `http://localhost:8080`.

## Default Credentials

- **Email**: `admin@proxima.local`
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
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **HTTP Client**: Axios
- **Icons**: Lucide React

## Data Storage

All data is stored locally:
- **Database**: `./data/proxima.db` (SQLite)
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

## Backend Implementation Files

### CMakeLists.txt
```cmake
cmake_minimum_required(VERSION 3.15)
project(proxima_qr)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/libs)
include_directories(${CMAKE_SOURCE_DIR}/libs/cpp-httplib)
include_directories(${CMAKE_SOURCE_DIR}/libs/json/include)
include_directories(${CMAKE_SOURCE_DIR}/libs/qrcodegen/cpp)
include_directories(${CMAKE_SOURCE_DIR}/libs/sqlite3)
include_directories(${CMAKE_SOURCE_DIR}/libs/stb)

# Source files
set(SOURCES
    src/main.cpp
    src/auth.cpp
    src/qr_generator.cpp
    src/storage.cpp
    src/templates.cpp
    libs/qrcodegen/cpp/qrcodegen.cpp
    libs/sqlite3/sqlite3.c
)

# Create executable
add_executable(proxima_qr ${SOURCES})

# Platform-specific settings
if(WIN32)
    target_link_libraries(proxima_qr ws2_32 wsock32)
else()
    target_link_libraries(proxima_qr pthread dl)
endif()

# Compiler flags
if(MSVC)
    target_compile_options(proxima_qr PRIVATE /W4)
else()
    target_compile_options(proxima_qr PRIVATE -Wall -Wextra)
endif()
```

## License

MIT License - Internal MVP for Proxima

## Author

Gasym A. Valiyev